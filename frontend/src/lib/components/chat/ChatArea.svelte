<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import { tick } from "svelte";
  import MessageBubble from "./MessageBubble.svelte";
  import MessageInput from "./MessageInput.svelte";
  import ModelSelector from "./ModelSelector.svelte";
  import {
    chatService,
    type ConversationDetail,
    type Message,
    type ModelChoice,
  } from "$services/chatService";
  import { authService } from "$services/auth";
  import { tStore } from "$stores/language";

  let {
    conversation = $bindable(null),
    selectedModels = $bindable([]),
    selectedProviderName = $bindable(""),
    selectedApiFormat = $bindable(""),
    selectedModelName = $bindable(""),
    selectedCategory = $bindable("middle"),
    sidebarCollapsed = $bindable(false),
  }: {
    conversation: ConversationDetail | null;
    selectedModels: ModelChoice[];
    selectedProviderName: string;
    selectedApiFormat: string;
    selectedModelName: string;
    selectedCategory: string;
    sidebarCollapsed: boolean;
  } = $props();

  const dispatch = createEventDispatcher<{
    conversationUpdate: { conversation: ConversationDetail };
    error: { message: string };
    modelSelected: ModelChoice;
    toggleSidebar: void;
  }>();

  function handleModelSelected(event: CustomEvent<ModelChoice>) {
    dispatch("modelSelected", event.detail);
  }

  // Group messages into user-assistant pairs for display
  function getMessageGroups() {
    const groups = [];

    // Simple chronological grouping - each user message followed by its assistant messages
    let currentUserMessage: Message | null = null;
    let currentAssistantMessages: Message[] = [];

    for (const msg of messages) {
      if (msg.role === "user") {
        // Save previous group if exists
        if (currentUserMessage) {
          groups.push({
            userMessage: currentUserMessage,
            assistantMessages: [...currentAssistantMessages] // Clone array
          });
        }

        // Start new group
        currentUserMessage = msg;
        currentAssistantMessages = [];
      } else if (msg.role === "assistant") {
        // Add to current assistant messages
        if (currentUserMessage) {
          currentAssistantMessages.push(msg);
        }
      }
    }

    // Save last group if exists
    if (currentUserMessage) {
      groups.push({
        userMessage: currentUserMessage,
        assistantMessages: [...currentAssistantMessages] // Clone array
      });
    }

    console.log("ChatArea: getMessageGroups - All messages:", $state.snapshot(messages));
    console.log("ChatArea: getMessageGroups - Groups created:", $state.snapshot(groups.map(g => ({
      userMessageId: g.userMessage?.id,
      assistantMessagesCount: g.assistantMessages.length,
      assistantMessageIds: g.assistantMessages.map(m => m.id),
      assistantMessages: g.assistantMessages
    }))));

    return groups;
  }

  let messages: Message[] = $state([]);
  let isLoading = $state(false);
  let streamingMessages: Record<number, string> = $state({});
  let streamingThinkings: Record<number, string> = $state({});
  let streamingCompleted: Record<number, boolean> = $state({});
  let _currentStreamingModels: ModelChoice[] = $state([]);
  let streamingFinished: Record<number, boolean> = $state({});

  // Track which message ID is currently being viewed for each model group (like open-webui)
  let currentViewingMessageIds: Record<string, number | null> = $state({});

  // Initialize currentViewingMessageIds from localStorage with conversation context
  let initializationComplete = $state(false);
  let hasLoadedMessageIds = $state(false);

  function initializeViewingMessageIds(conversationId?: number | string) {
    if (!initializationComplete && typeof window !== 'undefined') {
      try {
        const storageKey = conversationId ? `chatViewingMessageIds_${conversationId}` : 'chatViewingMessageIds';
        const saved = localStorage.getItem(storageKey);
        if (saved) {
          const parsed = JSON.parse(saved);
          if (parsed && typeof parsed === 'object') {
            currentViewingMessageIds = parsed;
            hasLoadedMessageIds = true;
          }
        }
      } catch (e) {
        console.warn("Failed to load viewing message IDs from localStorage:", e);
        currentViewingMessageIds = {};
      }
      initializationComplete = true;
    }
  }

  // Save currentViewingMessageIds to localStorage whenever it changes
  $effect(() => {
    if (typeof window !== 'undefined' && initializationComplete && hasLoadedMessageIds) {
      const storageKey = conversation?.id ? `chatViewingMessageIds_${conversation.id}` : 'chatViewingMessageIds';
      localStorage.setItem(storageKey, JSON.stringify(currentViewingMessageIds));
    }
  });

  // Re-initialize model selector when viewing message IDs change (with delay to avoid race condition)
  let reinitTimeout: ReturnType<typeof setTimeout> | null = null;
  $effect(() => {
    if (initializationComplete && hasLoadedMessageIds && messages.length > 0) {
      // Clear any pending timeout
      if (reinitTimeout) {
        clearTimeout(reinitTimeout);
      }
      // Delay to ensure currentViewingMessageIds are fully loaded
      reinitTimeout = setTimeout(() => {
        // Trigger model selector update by setting selectedModels to itself (will re-trigger the effect)
        selectedModels = [...selectedModels];
      }, 100);
    }
  });

  // Function to navigate through different results for a model (based on message ID like open-webui)
  function navigateResult(groupKey: string, direction: 'prev' | 'next', modelGroupMessages: Message[]) {
    const currentMessageId = currentViewingMessageIds[groupKey];
    let currentIndex: number;

    if (currentMessageId === null || currentMessageId === undefined) {
      // Default to showing the last message (most recent)
      currentIndex = modelGroupMessages.length - 1;
    } else {
      currentIndex = modelGroupMessages.findIndex(m => m.id === currentMessageId);
      if (currentIndex === -1) {
        // Message not found, default to last message
        currentIndex = modelGroupMessages.length - 1;
      }
    }

    let newIndex: number;
    if (direction === 'next') {
      newIndex = (currentIndex + 1) % modelGroupMessages.length;
    } else {
      newIndex = (currentIndex - 1 + modelGroupMessages.length) % modelGroupMessages.length;
    }

    // Update currentViewingMessageIds with the new message ID
    const newMessageId = modelGroupMessages[newIndex].id;
    currentViewingMessageIds = {
      ...currentViewingMessageIds,
      [groupKey]: newMessageId
    };
  }

  // Initialize when conversation is loaded
  $effect(() => {
    if (conversation?.id && !initializationComplete) {
      initializeViewingMessageIds(conversation.id);
    }
  });

  // Manage AbortControllers per conversation for strict isolation
  const conversationAbortControllers = new Map<number, AbortController>();
  let error: string | null = $state(null);
  let errorDetails: any = $state(null); // Store detailed error information
  let showErrorDetails = $state(false); // Toggle to show/hide error details
  let messagesContainer: HTMLDivElement;
  let userScrolledUp = $state(false); // Track if user manually scrolled up
  let isAtBottom = $state(true); // Track if user is at bottom

  // Extend Error interface to support additional properties
  interface ExtendedError extends Error {
    status?: number;
    statusText?: string;
    details?: any;
  }

  // 获取翻译函数
  const t = $derived($tStore);

  // Load messages when conversation changes
  // Use a flag to prevent multiple concurrent loads
  let lastLoadedConversationId = $state<number | null>(null);

  $effect(() => {
    if (conversation) {
      const conversationId = conversation.id;

      console.log("ChatArea: conversation changed:", {
        id: conversationId,
        lastLoadedId: lastLoadedConversationId,
        messageCountInConversation: conversation.messages?.length || 0,
        conversationMessages: conversation.messages,
        isSameAsLastLoaded: lastLoadedConversationId === conversationId
      });

      // Only load if this is a different conversation or first load
      if (lastLoadedConversationId !== conversationId) {
        console.log("ChatArea: Loading messages for new conversation:", conversationId);
        lastLoadedConversationId = conversationId;

        // Reset streaming state when switching conversations
        streamingMessages = {};
        streamingThinkings = {};
        streamingCompleted = {};
        streamingFinished = {};
        _currentStreamingModels = [];
        isLoading = false;
        error = null;
        errorDetails = null;

        loadMessages();
      } else {
        console.log("ChatArea: Skipping load - same conversation:", conversationId);
      }
    } else {
      // console.log("ChatArea: no conversation");
      messages = [];
      lastLoadedConversationId = null;

      // Reset all state when no conversation
      streamingMessages = {};
      streamingThinkings = {};
      streamingCompleted = {};
      streamingFinished = {};
      _currentStreamingModels = [];
      isLoading = false;
      error = null;
      errorDetails = null;
    }
  });

  async function loadMessages(force = false) {
    if (!conversation) return;

    console.log("ChatArea: loadMessages called:", {
      conversationId: conversation.id,
      force: force,
      currentMessagesCount: messages.length,
      conversationHasMessages: !!conversation.messages,
      conversationMessagesCount: conversation.messages?.length || 0
    });

    try {
      isLoading = true;
      error = null;
      errorDetails = null;

      // Always load fresh messages from the backend to prevent duplicates
      const detail = await chatService.getConversation(conversation.id);
      const loadedMessages = detail.messages || [];

      // Clear existing messages array before loading new messages
      messages = [];

      const uniqueIds = new Set(loadedMessages.map(m => m.id));
      console.log("ChatArea: Backend returned messages:", {
        backendMessageCount: loadedMessages.length,
        uniqueMessageIds: Array.from(uniqueIds),
        hasDuplicates: uniqueIds.size !== loadedMessages.length,
        backendMessages: loadedMessages
      });

      // Check if we have any streaming messages in progress
      const hasStreamingMessages = Object.keys(streamingMessages).length > 0;

      // Only skip loading if we're in the middle of streaming
      // Never skip loading based on cached conversation state to avoid duplicates
      if (!hasStreamingMessages || force) {
        // Always use the messages from the backend, not cached state
        // This is critical to prevent duplicate messages when refreshing the page
        // Additional safeguard: remove potential duplicates by message ID and content
        const uniqueMessages = [];
        const seenMessageIds = new Set();

        for (const message of loadedMessages) {
          // Skip if we've already seen this message ID
          if (seenMessageIds.has(message.id)) {
            console.log("ChatArea: Skipping duplicate message:", message.id);
            continue;
          }
          seenMessageIds.add(message.id);
          uniqueMessages.push(message);
        }

        // Preserve temporary user messages that haven't been saved to database yet
        // These have IDs generated with Date.now() (not from database)
        const tempUserMessages = messages.filter(m => m.role === "user" && !loadedMessages.some(dbMsg => dbMsg.id === m.id));
        const tempAssistantMessages = messages.filter(m => m.role === "assistant" && !loadedMessages.some(dbMsg => dbMsg.id === m.id));

        // Also preserve streaming messages that are currently being displayed
        // These are messages in the last user message group that have streaming state
        const streamingMessageContents = new Set(Object.values(streamingMessages));
        const streamingAssistantMessages = messages.filter(m =>
          m.role === "assistant" &&
          (streamingMessageContents.has(m.content as any) || m.isStreaming)
        );

        if (tempUserMessages.length > 0 || tempAssistantMessages.length > 0 || streamingAssistantMessages.length > 0) {
          console.log("ChatArea: Preserving temporary messages:", {
            tempUserMessages,
            tempAssistantMessages,
            streamingAssistantMessages
          });
          messages = [...uniqueMessages, ...tempUserMessages, ...tempAssistantMessages];
        } else {
          messages = uniqueMessages;
        }

        console.log("ChatArea: Set messages array:", {
          uniqueMessageCount: messages.length,
          messages: messages
        });

        // Update model selector based on the last user question and its assistant responses
        // Only update if not already set to avoid flicker on page refresh
        if (messages.length > 0 && (!selectedModels || selectedModels.length === 0)) {
          // Find the last user message to determine which models were actually used
          const lastUserMessageIndex = [...messages].reverse().findIndex(m => m.role === "user");

          if (lastUserMessageIndex !== -1) {
            const actualIndex = messages.length - 1 - lastUserMessageIndex;
            const lastUserMessage = messages[actualIndex];

            // Find all assistant messages that belong to this last user message (by parent_message_id)
            const assistantMessagesForLastQuestion = messages.filter(msg => {
              return msg.role === "assistant" && msg.parent_message_id === lastUserMessage.id;
            });

            console.log("ChatArea: Navigation count debug - BEFORE:", {
              lastUserMessageId: lastUserMessage.id,
              assistantMessagesCount: assistantMessagesForLastQuestion.length,
              assistantMessages: assistantMessagesForLastQuestion.map(m => ({ id: m.id, model: m.model, created_at: m.created_at }))
            });

            // Check for duplicate messages (same content and model)
            const uniqueMessages = new Map<string, Message>();
            assistantMessagesForLastQuestion.forEach(msg => {
              const key = `${msg.provider_name}-${msg.api_format}-${msg.model}-${msg.content}`;
              if (!uniqueMessages.has(key)) {
                uniqueMessages.set(key, msg);
              }
            });

            console.log("ChatArea: Navigation count debug - After deduplication:", {
              uniqueMessageCount: uniqueMessages.size,
              totalMessagesCount: assistantMessagesForLastQuestion.length,
              duplicateMessagesCount: assistantMessagesForLastQuestion.length - uniqueMessages.size
            });

            // Use unique messages for navigation count
            const uniqueAssistantMessages = Array.from(uniqueMessages.values());

            // For single-model scenario: show only the LAST retry (regardless of model changes)
            // For multi-model scenario: show latest model from each model subgroup
            const modelsList: ModelChoice[] = [];

            // Check if this is a single-model scenario (all messages have same provider/api_format combination)
            const uniqueProviderApiCombinations = new Set(
              uniqueAssistantMessages
                .filter(msg => msg.provider_name && msg.api_format && msg.model)
                .map(msg => `${msg.provider_name}-${msg.api_format}`)
            );

            const isSingleModelScenario = uniqueProviderApiCombinations.size === 1;

            if (isSingleModelScenario) {
              // Single model scenario: show ONLY the last retry (latest message)
              const sortedMessages = uniqueAssistantMessages
                .filter(msg => msg.provider_name && msg.api_format && msg.model)
                .sort((a, b) => {
                  const aTime = new Date(a.created_at || 0).getTime();
                  const bTime = new Date(b.created_at || 0).getTime();
                  return bTime - aTime;
                });

              if (sortedMessages.length > 0) {
                const latestMessage = sortedMessages[0];
                modelsList.push({
                  providerName: latestMessage.provider_name || '',
                  apiFormat: latestMessage.api_format || '',
                  model: latestMessage.model || '',
                });
              }
            } else {
              // Multi-model scenario: group by model configuration and get latest from each group
              const groupedModels = new Map<string, Message[]>();

              // First pass: group messages by model configuration
              uniqueAssistantMessages.forEach(msg => {
                if (msg.provider_name && msg.api_format && msg.model) {
                  const modelKey = `${msg.provider_name}-${msg.api_format}-${msg.model}`;
                  if (!groupedModels.has(modelKey)) {
                    groupedModels.set(modelKey, []);
                  }
                  groupedModels.get(modelKey)!.push(msg);
                }
              });

              // Second pass: for each group, get the latest message (by created_at)
              groupedModels.forEach((messages) => {
                const sortedMessages = messages.sort((a, b) => {
                  const aTime = new Date(a.created_at || 0).getTime();
                  const bTime = new Date(b.created_at || 0).getTime();
                  return bTime - aTime;
                });
                const latestMessage = sortedMessages[0];
                if (latestMessage && latestMessage.provider_name && latestMessage.api_format && latestMessage.model) {
                  modelsList.push({
                    providerName: latestMessage.provider_name,
                    apiFormat: latestMessage.api_format,
                    model: latestMessage.model,
                  });
                }
              });
            }

            if (modelsList.length > 0) {
              // For multi-model scenario, show only the currently selected model (based on navigation)
              // For single-model scenario, show the latest model
              if (!isSingleModelScenario && modelsList.length > 1) {
                // Multi-model scenario: find the currently selected model based on navigation state
                const lastUserMessageId = lastUserMessage.id;

                // Build model groups from assistant messages to maintain order
                const modelGroupsOrdered = new Map<string, Message[]>();
                const modelOrder: string[] = [];

                // First pass: group messages by model configuration while maintaining order
                uniqueAssistantMessages.forEach(msg => {
                  if (msg.provider_name && msg.api_format && msg.model) {
                    const modelKey = `${msg.provider_name}-${msg.api_format}-${msg.model}`;
                    if (!modelGroupsOrdered.has(modelKey)) {
                      modelGroupsOrdered.set(modelKey, []);
                      modelOrder.push(modelKey);
                    }
                    modelGroupsOrdered.get(modelKey)!.push(msg);
                  }
                });

                // Find the currently selected model based on navigation state
                let currentSelectedModelIndex = 0;
                let selectedModel: ModelChoice | null = null;

                // Check if currentViewingMessageIds are loaded before trying to find current model
                if (initializationComplete && hasLoadedMessageIds && Object.keys(currentViewingMessageIds).length > 0) {
                  // Iterate through model groups in order to find the currently selected one
                  for (let i = 0; i < modelOrder.length; i++) {
                    const modelKey = modelOrder[i];
                    const groupKey = `${lastUserMessageId}-${modelKey}`;

                    // Check if this model group has a current viewing message
                    const currentMessageId = currentViewingMessageIds[groupKey];
                    if (currentMessageId) {
                      currentSelectedModelIndex = i;
                      // Extract model info from modelKey (format: provider-api_format-model)
                      const [providerName, apiFormat, model] = modelKey.split('-');
                      selectedModel = {
                        providerName,
                        apiFormat,
                        model
                      };
                      break;
                    }
                  }

                  // If no current viewing message found, default to the last model (current latest)
                  if (!selectedModel) {
                    currentSelectedModelIndex = modelOrder.length - 1;
                    const lastModelKey = modelOrder[currentSelectedModelIndex];
                    const [providerName, apiFormat, model] = lastModelKey.split('-');
                    selectedModel = {
                      providerName,
                      apiFormat,
                      model
                    };
                  }
                } else {
                  // If viewing message IDs not loaded yet, show all models for now
                  // They will be updated when viewing message IDs are loaded
                  selectedModels = modelsList;
                  selectedProviderName = modelsList[0].providerName;
                  selectedApiFormat = modelsList[0].apiFormat;
                  selectedModelName = modelsList[0].model;
                }

                // If selectedModel is set (viewing IDs loaded), update to show only current model
                if (selectedModel) {
                  selectedModels = [selectedModel];
                  selectedProviderName = selectedModel.providerName;
                  selectedApiFormat = selectedModel.apiFormat;
                  selectedModelName = selectedModel.model;
                }
              } else {
                // Single model scenario or fallback
                const firstModel = modelsList[0];
                selectedModels = [firstModel];
                selectedProviderName = firstModel.providerName;
                selectedApiFormat = firstModel.apiFormat;
                selectedModelName = firstModel.model;
              }
            } else {
              // Fallback: find models from all assistant messages (not just last user question)
              const allAssistantMessages = messages.filter(msg => msg.role === "assistant");
              if (allAssistantMessages.length > 0) {
                // Group assistant messages by model configuration and get the latest from each group
                const groupedModels = new Map<string, Message[]>();

                allAssistantMessages.forEach(msg => {
                  if (msg.provider_name && msg.api_format && msg.model) {
                    const modelKey = `${msg.provider_name}-${msg.api_format}-${msg.model}`;
                    if (!groupedModels.has(modelKey)) {
                      groupedModels.set(modelKey, []);
                    }
                    groupedModels.get(modelKey)!.push(msg);
                  }
                });

                // Get latest message from each group
                const modelsList: ModelChoice[] = [];
                groupedModels.forEach((messages) => {
                  const sortedMessages = messages.sort((a, b) => {
                    const aTime = new Date(a.created_at || 0).getTime();
                    const bTime = new Date(b.created_at || 0).getTime();
                    return bTime - aTime;
                  });
                  const latestMessage = sortedMessages[0];
                  if (latestMessage?.provider_name && latestMessage?.api_format && latestMessage?.model) {
                    modelsList.push({
                      providerName: latestMessage.provider_name!,
                      apiFormat: latestMessage.api_format!,
                      model: latestMessage.model!,
                    });
                  }
                });

                if (modelsList.length > 0) {
                  // Check if this is a single-model scenario (all messages have same provider/api_format combination)
                  const uniqueProviderApiCombinations = new Set(
                    allAssistantMessages
                      .filter(msg => msg.provider_name && msg.api_format && msg.model)
                      .map(msg => `${msg.provider_name}-${msg.api_format}`)
                  );

                  const isSingleModelScenario = uniqueProviderApiCombinations.size === 1;

                  if (isSingleModelScenario) {
                    // Single model scenario: show ONLY the last retry (latest message)
                    const sortedMessages = allAssistantMessages
                      .filter(msg => msg.provider_name && msg.api_format && msg.model)
                      .sort((a, b) => {
                        const aTime = new Date(a.created_at || 0).getTime();
                        const bTime = new Date(b.created_at || 0).getTime();
                        return bTime - aTime;
                      });

                    if (sortedMessages.length > 0) {
                      const latestMessage = sortedMessages[0];
                      if (latestMessage && latestMessage.provider_name && latestMessage.api_format && latestMessage.model) {
                        selectedModels = [{
                          providerName: latestMessage.provider_name,
                          apiFormat: latestMessage.api_format,
                          model: latestMessage.model,
                        }];
                        selectedProviderName = latestMessage.provider_name;
                        selectedApiFormat = latestMessage.api_format;
                        selectedModelName = latestMessage.model;
                      }
                    }
                  } else {
                    // Multi-model scenario: show only the latest model (last in the list)
                    const latestModel = modelsList[modelsList.length - 1];
                    selectedModels = [latestModel];
                    selectedProviderName = latestModel.providerName;
                    selectedApiFormat = latestModel.apiFormat;
                    selectedModelName = latestModel.model;
                  }

                  console.log("ChatArea: Updated model selector from all messages (fallback with grouping):", {
                    selectedModels,
                    selectedProviderName,
                    selectedApiFormat,
                    selectedModelName
                  });
                }
              }
            }
          } else {
            // Fallback: find models from all assistant messages (not just last user question)
            const allAssistantMessages = messages.filter(msg => msg.role === "assistant");
            if (allAssistantMessages.length > 0) {
              // Check if this is a single-model scenario (all messages have same provider/api_format combination)
              const uniqueProviderApiCombinations = new Set(
                allAssistantMessages
                  .filter(msg => msg.provider_name && msg.api_format && msg.model)
                  .map(msg => `${msg.provider_name}-${msg.api_format}`)
              );

              const isSingleModelScenario = uniqueProviderApiCombinations.size === 1;
              const modelsList: ModelChoice[] = [];

              if (isSingleModelScenario) {
                // Single model scenario: show ONLY the last retry (latest message)
                const sortedMessages = allAssistantMessages
                  .filter(msg => msg.provider_name && msg.api_format && msg.model)
                  .sort((a, b) => {
                    const aTime = new Date(a.created_at || 0).getTime();
                    const bTime = new Date(b.created_at || 0).getTime();
                    return bTime - aTime;
                  });

                if (sortedMessages.length > 0) {
                  const latestMessage = sortedMessages[0];
                  modelsList.push({
                    providerName: latestMessage.provider_name || '',
                    apiFormat: latestMessage.api_format || '',
                    model: latestMessage.model || '',
                  });
                }
              } else {
                // Multi-model scenario: group by model configuration and get latest from each group
                const groupedModels = new Map<string, Message[]>();

                allAssistantMessages.forEach(msg => {
                  if (msg.provider_name && msg.api_format && msg.model) {
                    const modelKey = `${msg.provider_name}-${msg.api_format}-${msg.model}`;
                    if (!groupedModels.has(modelKey)) {
                      groupedModels.set(modelKey, []);
                    }
                    groupedModels.get(modelKey)!.push(msg);
                  }
                });

                // Get latest message from each group
                groupedModels.forEach((messages) => {
                  const sortedMessages = messages.sort((a, b) => {
                    const aTime = new Date(a.created_at || 0).getTime();
                    const bTime = new Date(b.created_at || 0).getTime();
                    return bTime - aTime;
                  });
                  const latestMessage = sortedMessages[0];
                  if (latestMessage && latestMessage.provider_name && latestMessage.api_format && latestMessage.model) {
                    modelsList.push({
                      providerName: latestMessage.provider_name,
                      apiFormat: latestMessage.api_format,
                      model: latestMessage.model,
                    });
                  }
                });
              }

              if (modelsList.length > 0) {
                // Show only the latest model (last in the list) for fallback
                const latestModel = modelsList[modelsList.length - 1];
                selectedModels = [latestModel];
                selectedProviderName = latestModel.providerName;
                selectedApiFormat = latestModel.apiFormat;
                selectedModelName = latestModel.model;
                console.log("ChatArea: Updated model selector from all messages (fallback - latest only):", {
                  selectedModels,
                  selectedProviderName,
                  selectedApiFormat,
                  selectedModelName
                });
              }
            }
          }
        } else if (messages.length > 0 && selectedModels && selectedModels.length > 0) {
          console.log("ChatArea: Skipping model selector update - already initialized from parent:", {
            selectedModels,
            selectedProviderName,
            selectedApiFormat,
            selectedModelName
          });
        }
      } else {
        // Streaming in progress - only update model selector, don't replace messages
        console.log("ChatArea: Skipping load due to active streaming");

        // Update model selector from loaded messages if available and not already set
        if (loadedMessages.length > 0 && (!selectedModels || selectedModels.length === 0)) {
          // Find the last user message to determine which models were actually used
          const lastUserMessageIndex = [...loadedMessages].reverse().findIndex(m => m.role === "user");

          if (lastUserMessageIndex !== -1) {
            const actualIndex = loadedMessages.length - 1 - lastUserMessageIndex;
            const lastUserMessage = loadedMessages[actualIndex];

            // Find all assistant messages that belong to this last user message (by parent_message_id)
            const assistantMessagesForLastQuestion = loadedMessages.filter(msg => {
              return msg.role === "assistant" && msg.parent_message_id === lastUserMessage.id;
            });

            // Check for duplicate messages (same content and model)
            const uniqueMessagesStreaming = new Map<string, Message>();
            assistantMessagesForLastQuestion.forEach(msg => {
              const key = `${msg.provider_name}-${msg.api_format}-${msg.model}-${msg.content}`;
              if (!uniqueMessagesStreaming.has(key)) {
                uniqueMessagesStreaming.set(key, msg);
              }
            });

            // Use unique messages for navigation count
            const uniqueAssistantMessages = Array.from(uniqueMessagesStreaming.values());

            // For single-model scenario: show only the LAST retry (regardless of model changes)
            // For multi-model scenario: show latest model from each model subgroup
            const modelsList: ModelChoice[] = [];

            // Check if this is a single-model scenario (all messages have same provider/api_format combination)
            const uniqueProviderApiCombinations = new Set(
              uniqueAssistantMessages
                .filter(msg => msg.provider_name && msg.api_format && msg.model)
                .map(msg => `${msg.provider_name}-${msg.api_format}`)
            );

            const isSingleModelScenario = uniqueProviderApiCombinations.size === 1;

            if (isSingleModelScenario) {
              // Single model scenario: show ONLY the last retry (latest message)
              const sortedMessages = uniqueAssistantMessages
                .filter(msg => msg.provider_name && msg.api_format && msg.model)
                .sort((a, b) => {
                  const aTime = new Date(a.created_at || 0).getTime();
                  const bTime = new Date(b.created_at || 0).getTime();
                  return bTime - aTime;
                });

              if (sortedMessages.length > 0) {
                const latestMessage = sortedMessages[0];
                modelsList.push({
                  providerName: latestMessage.provider_name || '',
                  apiFormat: latestMessage.api_format || '',
                  model: latestMessage.model || '',
                });
              }
            } else {
              // Multi-model scenario: group by model configuration and get latest from each group
              const groupedModels = new Map<string, Message[]>();

              // First pass: group messages by model configuration
              uniqueAssistantMessages.forEach(msg => {
                if (msg.provider_name && msg.api_format && msg.model) {
                  const modelKey = `${msg.provider_name}-${msg.api_format}-${msg.model}`;
                  if (!groupedModels.has(modelKey)) {
                    groupedModels.set(modelKey, []);
                  }
                  groupedModels.get(modelKey)!.push(msg);
                }
              });

              // Second pass: for each group, get the latest message (by created_at)
              groupedModels.forEach((messages) => {
                const sortedMessages = messages.sort((a, b) => {
                  const aTime = new Date(a.created_at || 0).getTime();
                  const bTime = new Date(b.created_at || 0).getTime();
                  return bTime - aTime;
                });
                const latestMessage = sortedMessages[0];
                if (latestMessage && latestMessage.provider_name && latestMessage.api_format && latestMessage.model) {
                  modelsList.push({
                    providerName: latestMessage.provider_name,
                    apiFormat: latestMessage.api_format,
                    model: latestMessage.model,
                  });
                }
              });
            }

            if (modelsList.length > 0) {
              selectedModels = modelsList;

              const firstModel = modelsList[0];
              selectedProviderName = firstModel.providerName;
              selectedApiFormat = firstModel.apiFormat;
              selectedModelName = firstModel.model;

              console.log("ChatArea: Updated model selector during streaming:", {
                selectedModels,
                selectedProviderName,
                selectedApiFormat,
                selectedModelName
              });
            }
          }
        } else if (loadedMessages.length > 0 && selectedModels && selectedModels.length > 0) {
          console.log("ChatArea: Skipping model selector update during streaming - already initialized from parent:", {
            selectedModels,
            selectedProviderName,
            selectedApiFormat,
            selectedModelName
          });
        }
      }
    } catch (err) {
      error = err instanceof Error ? err.message : t('common.error');
      errorDetails = {
        message: err instanceof Error ? err.message : t('common.error'),
        timestamp: new Date().toISOString()
      };
      console.error("Failed to load messages:", err);
    } finally {
      isLoading = false;
      // Reset scroll state only if not streaming
      if (!Object.keys(streamingMessages).length) {
        userScrolledUp = false;
        isAtBottom = true;

        // Scroll to bottom after loading with multiple attempts
        await tick();
        // Immediate scroll
        scrollToBottom();

        // Additional scroll after a short delay to ensure DOM is fully rendered
        setTimeout(() => {
          scrollToBottom();
        }, 50);
      }
    }
  }

  // Check if user is near bottom of scroll container
  function checkIfAtBottom() {
    if (!messagesContainer) return true;

    const threshold = 100; // pixels from bottom
    const { scrollTop, scrollHeight, clientHeight } = messagesContainer;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;

    return distanceFromBottom < threshold;
  }

  // Handle scroll events to detect user scrolling up
  function handleScroll() {
    if (!messagesContainer) return;

    isAtBottom = checkIfAtBottom();

    // If user scrolled up from bottom, mark it
    if (!isAtBottom) {
      userScrolledUp = true;
    } else {
      userScrolledUp = false;
    }
  }

  // Auto-scroll to bottom only if user hasn't scrolled up
  $effect(() => {
    if (messages.length > 0 || Object.keys(streamingMessages).length > 0 || Object.keys(streamingThinkings).length > 0) {
      // For streaming messages, use requestAnimationFrame for smoother scrolling
      // For regular messages, use a small delay to ensure DOM is ready
      const scrollAction = () => {
        // Only auto-scroll if user is at bottom or hasn't manually scrolled up
        if (!userScrolledUp && isAtBottom) {
          scrollToBottom();
        }
      };

      // Use requestAnimationFrame for streaming messages, setTimeout for others
      if (Object.keys(streamingMessages).length > 0 || Object.keys(streamingThinkings).length > 0) {
        requestAnimationFrame(scrollAction);
      } else {
        setTimeout(scrollAction, 0);
      }
    }
  });

  function scrollToBottom() {
    if (messagesContainer) {
      // Get current scroll position before scrolling
      const wasAtBottom = isAtBottom;
      const maxScrollTop = messagesContainer.scrollHeight - messagesContainer.clientHeight;

      // Always scroll to the bottom
      messagesContainer.scrollTop = maxScrollTop;

      // Use requestAnimationFrame for smoother scrolling, especially for streaming
      requestAnimationFrame(() => {
        if (messagesContainer) {
          messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
      });

      // Update state only if we were already at bottom or this is a user action
      if (wasAtBottom || userScrolledUp === false) {
        userScrolledUp = false;
        isAtBottom = true;
      }
    }
  }

  async function handleSendMessage(event: { message: string; selectedModels?: ModelChoice[]; skipAddUserMessage?: boolean; appendToExisting?: boolean; userMessageId?: number; streamingMessageId?: number }) {
    console.log("========================================");
    console.log("handleSendMessage called with:", event);

    if (!conversation) {
      console.error("✗ No conversation available");
      error = t('common.error');
      return;
    }

    if (!authService.isAuthenticated()) {
      console.error("✗ Not authenticated");
      error = t('common.error');
      return;
    }

    const chatId = conversation.id;
    console.log("Chat ID:", chatId);

    // Cancel any previous requests for this specific conversation
    const existingController = conversationAbortControllers.get(chatId);
    if (existingController) {
      console.log("Aborting existing controller for chat:", chatId);
      existingController.abort();
      conversationAbortControllers.delete(chatId);
    }

    // Create new AbortController for this conversation
    const abortController = new AbortController();
    conversationAbortControllers.set(chatId, abortController);

    // Check if we have selected models or conversation model
    // Use event.selectedModels if provided, otherwise use global selectedModels
    const modelsToUse = event.selectedModels && event.selectedModels.length > 0
      ? event.selectedModels
      : selectedModels.length > 0
        ? selectedModels
        : (selectedModelName || conversation.model
            ? [{
                providerName: selectedProviderName || conversation.provider_name || '',
                apiFormat: selectedApiFormat || conversation.api_format || '',
                model: selectedModelName || conversation.model || ''
              }]
            : []);

    console.log("ChatArea: Sending message details:", {
      selectedModelsLength: selectedModels.length,
      selectedModels: selectedModels,
      selectedModelName: selectedModelName,
      conversationModel: conversation.model,
      modelsToUse: modelsToUse,
      modelsToUseLength: modelsToUse.length,
      streamingMessageId: event.streamingMessageId,
      skipAddUserMessage: event.skipAddUserMessage
    });

    if (modelsToUse.length === 0) {
      console.error("✗ No models to use");
      error = t('common.error');
      return;
    }

    const userMessage = event.message;
    console.log("User message:", userMessage);
    error = null;

    // Reset scroll state when sending new message
    userScrolledUp = false;
    isAtBottom = true;

    console.log("ChatArea: Sending message to models:", modelsToUse);
    console.log("========================================");

    try {
      // Only add user message if not skipped (for retry scenarios)
      if (!event.skipAddUserMessage) {
        // Add user message to UI immediately for better UX
        const userMsg: Message = {
          id: Date.now(),
          role: "user",
          content: userMessage,
          provider_name: modelsToUse[0].providerName || null,
          api_format: modelsToUse[0].apiFormat || null,
          model: null,
          input_tokens: null,
          output_tokens: null,
          created_at: new Date().toISOString(),
        };

        // Check if this is the first user message before adding to messages array
        const isFirstMessage = messages.filter(m => m.role === "user").length === 0;
        if (isFirstMessage) {
          const generatedTitle = chatService.generateTitle(userMessage);
          const updatedConversation = await chatService.updateConversation(conversation.id, generatedTitle);
          // Update the conversation in parent component
          conversation = {
            ...conversation,
            title: updatedConversation.title
          };
          dispatch("conversationUpdate", { conversation });
          // Don't reload messages to preserve the UI state
          // The messages are already in the UI
        }

        messages = [...messages, userMsg];

        // Scroll to user message immediately
        await tick();
        scrollToBottom();
      }

      // Save user message to database (skip for retries to avoid duplicates)
      if (!event.skipAddUserMessage) {
        console.log("ChatArea: Adding message to database:", {
          conversationId: conversation.id,
          role: "user",
          content: userMessage,
        });
        await chatService.addMessage(
          conversation.id,
          "user",
          userMessage,
          null!,
          undefined, // thinking
          undefined, // inputTokens
          undefined, // outputTokens
          undefined, // provider
          undefined, // apiFormat
        );
      }

      // Initialize streaming state for all models
      // Use instance index as the key to support duplicate model selections
      streamingMessages = {};
      streamingThinkings = {};
      streamingCompleted = {};
      streamingFinished = {};
      _currentStreamingModels = [...modelsToUse]; // Store current models for template access
      modelsToUse.forEach((_model, index) => {
        streamingMessages[index] = "";
        streamingThinkings[index] = "";
        streamingCompleted[index] = false;
        streamingFinished[index] = false;
      });
      isLoading = true;

      // Send to all selected models
      const promises = modelsToUse.map(async (model, index) => {
        await chatService.sendChatMessage(
          {
            ...conversation!,
            provider_name: model.providerName,
            api_format: model.apiFormat,
            model: model.model,
            messages: messages,
          },
          userMessage,
          (chunk, thinking) => {
            if (chunk) {
              // Update streaming state
              const newContent = (streamingMessages[index] || "") + chunk;
              streamingMessages = {
                ...streamingMessages,
                [index]: newContent
              };

              // If this is a retry (streamingMessageId provided), update the message directly
              if (event.streamingMessageId) {
                messages = messages.map(m => {
                  if (m.id === event.streamingMessageId) {
                    return {
                      ...m,
                      content: newContent,  // Use newContent instead of m.content + chunk
                      isStreaming: true
                    };
                  }
                  return m;
                });
              }

              // Scroll immediately when new chunk arrives for smooth streaming experience
              if (!userScrolledUp && isAtBottom) {
                scrollToBottom();
              }
            }
            if (thinking !== undefined) {
              streamingThinkings = {
                ...streamingThinkings,
                [index]: thinking
              };

              // If this is a retry, update the message directly
              if (event.streamingMessageId) {
                messages = messages.map(m => {
                  if (m.id === event.streamingMessageId) {
                    return {
                      ...m,
                      thinking: thinking
                    };
                  }
                  return m;
                });
              }

              // Scroll immediately when thinking content updates
              if (!userScrolledUp && isAtBottom) {
                scrollToBottom();
              }
            }
          },
          async (usage) => {
            // On complete for this model
            const assistantMessage = streamingMessages[index] || "";
            const thinkingContent = streamingThinkings[index];

            // Prevent duplicate onComplete calls from saving multiple times
            // Set streamingCompleted flag immediately when onComplete is first called
            if (streamingCompleted[index]) {
              return;
            }

            if (assistantMessage) {
              // Mark as completed BEFORE saving to prevent race condition
              streamingCompleted = {
                ...streamingCompleted,
                [index]: true
              };
              streamingFinished = {
                ...streamingFinished,
                [index]: true
              };
              // Always save to database, including for retry messages
              // This ensures we have a complete history of all messages including retries
              await chatService.addMessage(
                conversation!.id,
                "assistant",
                assistantMessage,
                model.model,
                thinkingContent || undefined,
                usage?.input_tokens,
                usage?.output_tokens,
                model.providerName || undefined,
                model.apiFormat || undefined,
                event.userMessageId,
              ).catch(err => {
                console.error("Failed to save assistant message:", err);
              });

              // If this was a retry, update the frontend message state
              if (event.streamingMessageId) {
                messages = messages.map(m => {
                  if (m.id === event.streamingMessageId) {
                    return {
                      ...m,
                      content: assistantMessage,
                      thinking: thinkingContent,
                      input_tokens: usage?.input_tokens || null,
                      output_tokens: usage?.output_tokens || null,
                      isStreaming: false  // Ensure streaming state is reset
                    };
                  }
                  return m;
                });
              }
            }

            // Check if all models are done
            let allCompleted = true;
            for (const key in streamingCompleted) {
              if (!streamingCompleted[key]) {
                allCompleted = false;
                break;
              }
            }

            if (allCompleted) {
              // All streams completed - reload messages to get the latest state from database
              isLoading = false;

              console.log("ChatArea: All streams completed, messages before reload:", messages);

              // Reload messages to ensure we have the latest database state
              // This ensures correct result counting (e.g., 4/5 instead of losing the count)
              // Skip reload if this is a retry (streamingMessageId provided) to avoid reverting to old content
              if (!event.streamingMessageId) {
                setTimeout(async () => {
                  await loadMessages(true); // Force reload to get latest state
                  console.log("ChatArea: Messages reloaded after completion");

                  // Clear streaming state after reload to avoid flash
                  streamingMessages = {};
                  streamingThinkings = {};
                  streamingCompleted = {};
                  streamingFinished = {};
                  _currentStreamingModels = [];
                }, 100); // Small delay to ensure database writes are complete
              } else {
                console.log("ChatArea: Skipping reload for retry message");
                // For retry messages, clear streaming state immediately since we already updated the message
                streamingMessages = {};
                streamingThinkings = {};
                streamingCompleted = {};
                streamingFinished = {};
                _currentStreamingModels = [];
              }

              // Scroll to bottom
              await tick();
              scrollToBottom();

              // Cleanup AbortController after successful completion
              conversationAbortControllers.delete(chatId);
            }
          },
          (err) => {
            // Type assert to ExtendedError to access additional properties
            const extendedErr = err as ExtendedError;

            // Store detailed error information
            error = extendedErr.message;
            errorDetails = {
              message: extendedErr.message,
              status: extendedErr.status,
              statusText: extendedErr.statusText,
              details: extendedErr.details,
              timestamp: new Date().toISOString()
            };

            console.error("Chat message error for model", model.model, ":", err);

            // Mark this stream as completed (even though it errored)
            streamingCompleted = {
              ...streamingCompleted,
              [index]: true
            };

            // Check if all models are done
            let allCompleted = true;
            for (const key in streamingCompleted) {
              if (!streamingCompleted[key]) {
                allCompleted = false;
                break;
              }
            }

            if (allCompleted) {
              // All streams completed (with or without errors) - cleanup
              isLoading = false;
              // Clear streaming state
              streamingMessages = {};
              streamingThinkings = {};
              streamingCompleted = {};
              streamingFinished = {};
              _currentStreamingModels = [];

              // Cleanup AbortController after completion (with or without errors)
              conversationAbortControllers.delete(chatId);
            }

            dispatch("error", { message: extendedErr.message });
          },
          abortController
        );
      });

      await Promise.all(promises);
    } catch (err) {
      error = err instanceof Error ? err.message : t('common.error');
      streamingMessages = {};
      streamingThinkings = {};
      streamingCompleted = {};
      streamingFinished = {};
      _currentStreamingModels = [];
      isLoading = false;
      dispatch("error", { message: error });

      // Cleanup AbortController on error
      conversationAbortControllers.delete(chatId);
    }
  }

  function handleRetryModel(event: { providerName: string; apiFormat: string; model: string }) {
    const { providerName, apiFormat, model } = event;
    console.log("========================================");
    console.log("Retrying model:", { providerName, apiFormat, model });
    console.log("Current messages array:", messages.length, "messages");
    console.log("currentViewingMessageIds:", $state.snapshot(currentViewingMessageIds));

    // Debug: print all assistant messages
    const assistantMessages = messages.filter(m => m.role === "assistant");
    console.log("All assistant messages:", assistantMessages.map(m => ({
      id: m.id,
      provider_name: m.provider_name,
      api_format: m.api_format,
      model: m.model,
      parent_message_id: (m as any).parent_message_id,
      content: m.content.substring(0, 50) + "..."
    })));

    // Find the LAST assistant message that matches this model
    // In multi-model scenarios, we want the most recent message for this model
    let retryingMessageIndex = -1;
    let retryingMessage = null;

    // Search backwards through messages to find the most recent matching message
    for (let i = messages.length - 1; i >= 0; i--) {
      const msg = messages[i];
      console.log(`Checking message ${i}:`, {
        id: msg.id,
        role: msg.role,
        provider_name: msg.provider_name,
        api_format: msg.api_format,
        model: msg.model,
        matches: msg.role === "assistant" &&
          msg.provider_name?.toLowerCase() === providerName.toLowerCase() &&
          msg.api_format?.toLowerCase() === apiFormat.toLowerCase() &&
          msg.model?.toLowerCase() === model.toLowerCase()
      });

      if (msg.role === "assistant" &&
          msg.provider_name?.toLowerCase() === providerName.toLowerCase() &&
          msg.api_format?.toLowerCase() === apiFormat.toLowerCase() &&
          msg.model?.toLowerCase() === model.toLowerCase()) {
        retryingMessageIndex = i;
        retryingMessage = msg;
        console.log("✓ Found matching message at index", i);
        break;
      }
    }

    console.log("Retry message search result:", {
      retryingMessageIndex,
      targetModel: `${providerName}-${apiFormat}-${model}`,
      foundMessage: retryingMessageIndex !== -1 ? messages[retryingMessageIndex] : null
    });

    if (retryingMessageIndex !== -1 && retryingMessage) {
      let userMessage: Message | null = null;

      // Try to find user message using parent_message_id first (modern mode)
      if ((retryingMessage as any).parent_message_id) {
        userMessage = messages.find(m => m.id === (retryingMessage as any).parent_message_id) || null;
        console.log("Found user message via parent_message_id:", userMessage?.id);
      }

      // Fallback: Find the user message by searching backwards from the retrying message
      if (!userMessage) {
        console.log("parent_message_id not found, searching backwards for user message...");
        for (let i = retryingMessageIndex - 1; i >= 0; i--) {
          const msg = messages[i];
          console.log(`Checking message ${i} for user message:`, {
            id: msg.id,
            role: msg.role,
            content: msg.content.substring(0, 50)
          });
          if (msg.role === "user") {
            userMessage = msg;
            console.log("✓ Found user message by backwards search at index", i, ":", userMessage.id);
            break;
          }
        }
      }

      if (userMessage && userMessage.role === "user") {
        console.log("✓ Retrying message:", retryingMessage.id, "with userMessage:", userMessage.id);

        // Create a new assistant message for the retry (new database record)
        const newRetryMessageId = Date.now(); // Temporary ID for UI
        console.log("Creating new retry message with temp ID:", newRetryMessageId);

        // Add the new retry message to the messages array
        const newRetryMessage: Message = {
          id: newRetryMessageId,
          role: "assistant",
          content: "",
          thinking: "",
          isStreaming: true,
          model: model,
          provider_name: providerName,
          api_format: apiFormat,
          parent_message_id: userMessage.id,
          input_tokens: null,
          output_tokens: null,
          created_at: new Date().toISOString()
        };

        messages = [...messages, newRetryMessage];

        // Update navigation index to show the latest message (new retry)
        const groupKey = `${userMessage.id}-${providerName}-${apiFormat}-${model}`;
        currentViewingMessageIds = {
          ...currentViewingMessageIds,
          [groupKey]: newRetryMessageId
        };

        console.log("Updating navigation:", { groupKey, newRetryMessageId });
        console.log("Updated currentViewingMessageIds:", $state.snapshot(currentViewingMessageIds));

        // Start streaming new response
        console.log("Calling handleSendMessage with streamingMessageId:", newRetryMessageId);
        handleSendMessage({
          message: userMessage.content,
          userMessageId: userMessage.id,
          selectedModels: [{ providerName, apiFormat, model }],
          skipAddUserMessage: true,
          appendToExisting: true,
          streamingMessageId: newRetryMessageId
        });

        console.log("✓ Retry initiated with new message ID:", newRetryMessageId);
        console.log("========================================");
      } else {
        console.error("✗ User message not found for retry");
        console.log("========================================");
      }
    } else {
      console.error("✗ Retry message not found");
      console.warn("Retry message search details:", {
        providerName,
        apiFormat,
        model,
        totalMessages: messages.length,
        assistantMessagesCount: assistantMessages.length
      });
      console.log("========================================");
    }
  }

  async function handleEditMessage(event: { message: any; newContent: string }) {
    if (!conversation) return;

    const { message, newContent } = event;

    try {
      // Update the message in the local state
      messages = messages.map((msg) =>
        msg.id === message.id ? { ...msg, content: newContent } : msg
      );

      // Update conversation state
      if (conversation) {
        const updatedConversation = {
          ...conversation,
          messages: messages,
        };
        conversation = updatedConversation;
        dispatch("conversationUpdate", { conversation: updatedConversation });
      }

      // Retry the message (send it again with the new content)
      // Remove the old assistant message if it exists
      const messageIndex = messages.findIndex((msg) => msg.id === message.id);
      if (messageIndex !== -1 && messageIndex < messages.length - 1) {
        // Check if next message is an assistant message that was a response to this message
        const nextMessage = messages[messageIndex + 1];
        if (nextMessage && nextMessage.role === "assistant") {
          // Remove the assistant message that followed this user message
          messages = messages.filter((msg) => msg.id !== nextMessage.id);
        }
      }

      // Now resend with new content
      await handleSendMessage({ message: newContent });
    } catch (err) {
      error = err instanceof Error ? err.message : t('common.error');
      console.error("Failed to edit message:", err);
      dispatch("error", { message: error });
    }
  }
</script>

<div class="chat-area">
  <!-- Model Selector - Top Left Corner -->
  <div class="model-selector-container">
    <!-- Expand Sidebar Button - Only show when sidebar is collapsed -->
    {#if sidebarCollapsed}
      <button class="expand-sidebar-btn" onclick={() => dispatch("toggleSidebar")} title={t('chat.expandSidebar')}>
        <span class="hamburger-icon">
          <span class="line line-1"></span>
          <span class="line line-2"></span>
          <span class="line line-3"></span>
        </span>
      </button>
    {/if}

    <ModelSelector
      bind:selectedModels={selectedModels}
      bind:selectedProviderName={selectedProviderName}
      bind:selectedApiFormat={selectedApiFormat}
      bind:selectedModelName={selectedModelName}
      bind:selectedCategory={selectedCategory}
      on:modelSelected={handleModelSelected}
    />
  </div>

  <div
    class="messages-container"
    bind:this={messagesContainer}
    onscroll={handleScroll}
  >
    {#if !conversation}
      <div class="welcome">
        <h2>{t('chatArea.welcomeTitle')}</h2>
        <p>{t('chatArea.welcomeDescription')}</p>
      </div>
    {:else if isLoading && messages.length === 0}
      <div class="loading">
        <div class="spinner"></div>
        <p>{t('common.loading')}</p>
      </div>
    {:else if error}
      <div class="error-container">
        <div class="error-icon">⚠</div>
        <div class="error-content">
          <h3>{t('common.error')}</h3>
          <p class="error-message">{error}</p>

          <!-- Show error details in development or when available -->
          {#if errorDetails}
            <button
              class="toggle-details-btn"
              onclick={() => showErrorDetails = !showErrorDetails}
            >
              {showErrorDetails ? 'Hide' : 'Show'} Details
            </button>

            {#if showErrorDetails}
              <div class="error-details">
                {#if errorDetails.status}
                  <div class="error-detail-item">
                    <strong>Status:</strong>
                    <span>{errorDetails.status} {errorDetails.statusText}</span>
                  </div>
                {/if}

                <!-- New structured error fields from backend -->
                {#if errorDetails.type}
                  <div class="error-detail-item">
                    <strong>Error Type:</strong>
                    <span>{errorDetails.type}</span>
                  </div>
                {/if}

                {#if errorDetails.provider}
                  <div class="error-detail-item">
                    <strong>Provider:</strong>
                    <span>{errorDetails.provider}</span>
                  </div>
                {/if}

                {#if errorDetails.model}
                  <div class="error-detail-item">
                    <strong>Model:</strong>
                    <span>{errorDetails.model}</span>
                  </div>
                {/if}

                {#if errorDetails.request_id}
                  <div class="error-detail-item">
                    <strong>Request ID:</strong>
                    <span>{errorDetails.request_id}</span>
                  </div>
                {/if}

                {#if errorDetails.provider_status_code}
                  <div class="error-detail-item">
                    <strong>Provider Status:</strong>
                    <span>{errorDetails.provider_status_code}</span>
                  </div>
                {/if}

                {#if errorDetails.provider_url}
                  <div class="error-detail-item">
                    <strong>Provider URL:</strong>
                    <span class="error-url">{errorDetails.provider_url}</span>
                  </div>
                {/if}

                {#if errorDetails.status_code}
                  <div class="error-detail-item">
                    <strong>Backend Status:</strong>
                    <span>{errorDetails.status_code}</span>
                  </div>
                {/if}

                <!-- Network error category (ssl_error, dns_error, timeout_error, etc.) -->
                {#if errorDetails.category}
                  <div class="error-detail-item">
                    <strong>Error Category:</strong>
                    <span class="error-category {errorDetails.category}">{errorDetails.category}</span>
                  </div>
                {/if}

                <!-- User-friendly hint for network errors -->
                {#if errorDetails.hint}
                  <div class="error-detail-item">
                    <strong>Hint:</strong>
                    <span class="error-hint">{errorDetails.hint}</span>
                  </div>
                {/if}

                {#if errorDetails.details}
                  <div class="error-detail-item">
                    <strong>Full Details:</strong>
                    <pre>{JSON.stringify(errorDetails.details, null, 2)}</pre>
                  </div>
                {/if}

                {#if errorDetails.timestamp}
                  <div class="error-detail-item">
                    <strong>Time:</strong>
                    <span>{new Date(errorDetails.timestamp).toLocaleString()}</span>
                  </div>
                {/if}
              </div>
            {/if}
          {/if}
        </div>

        <div class="error-actions">
          <button class="retry-btn" onclick={() => loadMessages()}>
            {t('messageBubble.retry')}
          </button>
        </div>
      </div>
    {:else if messages.length === 0}
      <div class="empty">
        <p>{t('chatArea.startConversation')}</p>
      </div>
    {:else}
      {@const messageGroups = getMessageGroups()}

      {#each messageGroups as group}
        <!-- Render user message only once per group (first occurrence) -->
        {#if group.userMessage}
          <MessageBubble
            message={group.userMessage}
            showModel={false}
            showTokens={true}
            providerName={group.userMessage.provider_name ?? selectedProviderName ?? (conversation?.provider_name ?? null)}
            apiFormat={group.userMessage.api_format ?? selectedApiFormat ?? (conversation?.api_format ?? null)}
            onedit={handleEditMessage}
          />
        {/if}

        <!-- Render all assistant messages for this user message, grouped by model -->
        {#if group.assistantMessages.length > 0 || Object.keys(streamingMessages).length > 0}
          {@const groupedByModel = group.assistantMessages.reduce((acc, msg) => {
            // Group messages by model configuration
            // All retries of the same model should be in the same group
            const baseKey = `${msg.provider_name}-${msg.api_format}-${msg.model}`;

            if (!acc[baseKey]) {
              acc[baseKey] = [];
            }
            acc[baseKey].push(msg);
            return acc;
          }, {} as Record<string, typeof group.assistantMessages>)}

          <div class="assistant-messages-grid">
            {#if group.assistantMessages.length > 0}
              {#each Object.entries(groupedByModel) as [modelKey, modelGroupMessages]}
                {@const groupKey = `${group.userMessage?.id}-${modelKey}`}
                {@const currentMessageId = currentViewingMessageIds[groupKey]}
                {@const currentIndex = currentMessageId !== null && currentMessageId !== undefined
                  ? modelGroupMessages.findIndex(m => m.id === currentMessageId)
                  : modelGroupMessages.length - 1}
                {@const validIndex = currentIndex >= 0 ? currentIndex : modelGroupMessages.length - 1}
                {@const currentMessage = modelGroupMessages[validIndex]}
                {@const modelName = currentMessage?.model}
                {@const providerName = currentMessage?.provider_name}
                {@const apiFormat = currentMessage?.api_format}
                {@const isStreaming = currentMessage ? (currentMessage.isStreaming || `${providerName}-${apiFormat}-${modelName}` in streamingMessages) : false}

                {#if currentMessage}
                  <!-- Calculate correct resultIndex and totalResults for this model group -->
                  {@const resultIndex = validIndex}
                  <!-- Each model should have independent navigation showing its own retry count -->
                  {@const totalResults = modelGroupMessages.length}
                  <!-- DEBUG: Log navigation calculation -->
                  {console.log('Navigation Debug:', {
                    userMessageId: group.userMessage?.id,
                    modelKey,
                    modelGroupMessagesCount: modelGroupMessages.length,
                    modelGroupMessagesIds: modelGroupMessages.map(m => m.id),
                    totalResults,
                    validIndex,
                    currentMessageId: currentMessage?.id
                  })}
                  <!-- Always show navigation for assistant messages, especially for retry functionality -->
                  {@const shouldShowNav = true}

                  <div class="assistant-message-column">
                    <MessageBubble
                      message={currentMessage}
                      isStreaming={isStreaming}
                      showModel={true}
                      showTokens={!isStreaming}
                      providerName={providerName ?? selectedProviderName ?? (conversation?.provider_name ?? null)}
                      apiFormat={apiFormat ?? selectedApiFormat ?? (conversation?.api_format ?? null)}
                      onretryModel={handleRetryModel}
                      onedit={handleEditMessage}
                      resultIndex={resultIndex}
                      totalResults={totalResults}
                      showResultNavigation={shouldShowNav}
                      onNavigatePrev={() => navigateResult(groupKey, 'prev', modelGroupMessages)}
                      onNavigateNext={() => navigateResult(groupKey, 'next', modelGroupMessages)}
                    />
                  </div>
                {/if}
              {/each}
            {:else if Object.keys(streamingMessages).length > 0}
              <!-- Render streaming messages when no finalized messages yet -->
              {#each Object.entries(streamingMessages) as [index, content]}
                {@const model = _currentStreamingModels[Number(index)]}
                {@const providerName = model.providerName}
                {@const apiFormat = model.apiFormat}
                {@const modelName = model.model}

                <!-- Calculate correct resultIndex and totalResults for streaming messages -->
                <!-- For streaming messages, we need to find the model group and calculate the correct index -->
                {@const baseModelKey = `${providerName}-${apiFormat}-${modelName}`}
                <!-- Find all assistant messages for THIS user message that match this model -->
                <!-- Use the current group's userMessage, not all messages -->
                {@const userMessage = group.userMessage}
                {@const modelGroupMessagesForStreaming = messages.filter(msg =>
                  msg.role === "assistant" &&
                  msg.parent_message_id === userMessage?.id &&
                  msg.provider_name === providerName &&
                  msg.api_format === apiFormat &&
                  msg.model === modelName
                )}
                <!-- Generate model key consistent with grouping logic (no instance suffix) -->
                {@const modelKey = baseModelKey}
                {@const groupKey = `${userMessage?.id}-${modelKey}`}
                <!-- For streaming messages, show only the existing count (streaming message not saved yet) -->
                <!-- If there are 0 existing messages, show 0/1 (0 saved, 1 total after save) -->
                <!-- If there is 1 existing message, show 1/2 (1 saved, 2 total after save) -->
                {@const currentStreamingIndex = modelGroupMessagesForStreaming.length}
                {@const totalResultsForStreaming = modelGroupMessagesForStreaming.length + 1}
                <!-- Always show navigation for streaming messages -->
                {@const showResultNavigation = true}
                <!-- DEBUG: Log streaming navigation calculation -->
                {console.log('Streaming Navigation Debug:', {
                  index,
                  modelName,
                  providerName,
                  apiFormat,
                  currentStreamingIndex,
                  totalResultsForStreaming,
                  userMessageId: userMessage?.id,
                  existingMessagesCount: modelGroupMessagesForStreaming.length,
                  modelKey,
                  modelGroupMessagesIds: modelGroupMessagesForStreaming.map(m => m.id)
                })}
                <div class="assistant-message-column">
                  <MessageBubble
                    message={{
                      id: Date.now() + Number(index),
                      role: "assistant",
                      content: content,
                      thinking: streamingThinkings[Number(index)] || undefined,
                      model: modelName,
                      input_tokens: null,
                      output_tokens: null,
                      created_at: new Date().toISOString(),
                      provider_name: providerName,
                      api_format: apiFormat,
                    } as any}
                    isStreaming={!streamingFinished[Number(index)]}
                    showModel={true}
                    showTokens={false}
                    providerName={providerName}
                    apiFormat={apiFormat}
                    onretryModel={handleRetryModel}
                    resultIndex={currentStreamingIndex}
                    totalResults={totalResultsForStreaming}
                    showResultNavigation={showResultNavigation}
                    onNavigatePrev={() => navigateResult(groupKey, 'prev', modelGroupMessagesForStreaming)}
                    onNavigateNext={() => navigateResult(groupKey, 'next', modelGroupMessagesForStreaming)}
                  />
                </div>
              {/each}
            {/if}
          </div>
        {/if}
      {/each}

    {/if}
  </div>

  <!-- Scroll to bottom button -->
  {#if userScrolledUp && !isAtBottom}
    <button
      class="scroll-to-bottom"
      onclick={scrollToBottom}
      title={t('chatArea.scrollToBottom')}
    >
      ↓
    </button>
  {/if}

  <div class="input-container">
    {#if conversation && selectedModels.length > 0}
      <MessageInput
        disabled={isLoading}
        placeholder={t('messageInput.placeholder')}
        hasMessages={messages.length > 0}
        onsend={handleSendMessage}
      />
    {:else if conversation && selectedModels.length === 0}
      <div class="no-model-prompt">
        <p>{t('chatArea.selectModelFirst')}</p>
      </div>
    {:else}
      <div class="no-conversation-prompt">
        <p>{t('chatArea.startConversation')}</p>
      </div>
    {/if}
  </div>
</div>

<style>
  .chat-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    height: 100%;
    position: relative;
  }

  .model-selector-container {
    flex-shrink: 0;
    background: transparent;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 1rem;
    padding-left: 1rem;
    position: relative;
    z-index: 9998;
  }

  .expand-sidebar-btn {
    padding: 0.5rem;
    background: transparent;
    color: var(--text-secondary);
    border: none;
    border-radius: 0.375rem;
    cursor: pointer;
    transition: all 0.2s ease;
    min-width: 32px;
    min-height: 32px;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .expand-sidebar-btn:hover {
    background: var(--bg-secondary);
    color: var(--text-primary);
    transform: scale(1.05);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }

  .expand-sidebar-btn:active {
    transform: scale(0.98);
  }

  .expand-sidebar-btn .hamburger-icon {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    width: 18px;
    height: 14px;
  }

  .expand-sidebar-btn .hamburger-icon .line {
    display: block;
    height: 2px;
    background: currentColor;
    border-radius: 1px;
    transition: all 0.2s ease;
  }

  .expand-sidebar-btn .hamburger-icon .line-1 {
    width: 100%;
  }

  .expand-sidebar-btn .hamburger-icon .line-2 {
    width: 65%;
    align-self: flex-end;
  }

  .expand-sidebar-btn .hamburger-icon .line-3 {
    width: 100%;
  }

  .expand-sidebar-btn:hover .hamburger-icon .line {
    background: var(--text-primary);
  }

  .messages-container {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 2rem;
    padding-bottom: 3rem; /* 增加底部间距，避免消息贴着底部 */
    background: linear-gradient(
      to bottom,
      var(--bg-secondary) 0%,
      var(--bg-primary) 100%
    );
    min-height: 0;
    scroll-behavior: smooth;
  }

  .input-container {
    flex-shrink: 0;
    background: var(--bg-primary);
    border-top: 1px solid var(--border-color);
    box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.05);
  }

  .no-model-prompt {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100px;
    padding: 1rem;
    text-align: center;
    color: var(--text-secondary);
    font-size: 0.9rem;
  }

  /* Custom scrollbar */
  .messages-container::-webkit-scrollbar {
    width: 8px;
  }

  .messages-container::-webkit-scrollbar-track {
    background: transparent;
  }

  .messages-container::-webkit-scrollbar-thumb {
    background: var(--border-color);
    border-radius: 4px;
    transition: background 0.2s;
  }

  .messages-container::-webkit-scrollbar-thumb:hover {
    background: var(--text-tertiary);
  }

  /* Empty states */
  .welcome,
  .loading,
  .empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    text-align: center;
    color: var(--text-secondary);
    padding: 2rem;
  }

  .welcome h2 {
    font-size: 1.75rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 0.75rem;
    background: linear-gradient(135deg, var(--primary-color), #6ba5ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .welcome p {
    font-size: 1rem;
    opacity: 0.8;
  }

  .empty {
    opacity: 0.7;
  }

  .empty p {
    font-size: 1rem;
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 3px solid var(--border-color);
    border-top: 3px solid var(--primary-color);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin-bottom: 1rem;
  }

  @keyframes spin {
    0% {
      transform: rotate(0deg);
    }
    100% {
      transform: rotate(360deg);
    }
  }

  /* Enhanced error display */
  .error-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 3rem 2rem;
    text-align: center;
    color: var(--text-secondary);
    background: rgba(239, 68, 68, 0.05);
    border: 1px solid rgba(239, 68, 68, 0.2);
    border-radius: 1rem;
    margin: 2rem;
    max-width: 600px;
    margin-left: auto;
    margin-right: auto;
  }

  .error-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
    color: #ef4444;
  }

  .error-content {
    width: 100%;
  }

  .error-content h3 {
    color: #ef4444;
    font-size: 1.5rem;
    font-weight: 600;
    margin-bottom: 1rem;
  }

  .error-message {
    color: var(--text-primary);
    font-size: 1rem;
    margin-bottom: 1rem;
    word-break: break-word;
  }

  .toggle-details-btn {
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.3);
    padding: 0.5rem 1rem;
    border-radius: 0.5rem;
    cursor: pointer;
    font-size: 0.875rem;
    margin-bottom: 1rem;
    transition: all 0.2s;
  }

  .toggle-details-btn:hover {
    background: rgba(239, 68, 68, 0.2);
    transform: translateY(-1px);
  }

  .error-details {
    background: var(--bg-tertiary);
    border: 1px solid var(--border-color);
    border-radius: 0.5rem;
    padding: 1rem;
    margin-top: 1rem;
    text-align: left;
    max-height: 300px;
    overflow-y: auto;
  }

  .error-detail-item {
    margin-bottom: 0.75rem;
    font-size: 0.875rem;
  }

  .error-detail-item:last-child {
    margin-bottom: 0;
  }

  .error-detail-item strong {
    color: var(--text-primary);
    display: block;
    margin-bottom: 0.25rem;
  }

  .error-detail-item span,
  .error-detail-item pre {
    color: var(--text-secondary);
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 0.8125rem;
    word-break: break-word;
    white-space: pre-wrap;
  }

  .error-url {
    color: var(--primary-color);
    text-decoration: none;
    word-break: break-all;
  }

  .error-url:hover {
    text-decoration: underline;
    color: var(--primary-hover);
  }

  .error-category {
    padding: 0.25rem 0.5rem;
    border-radius: 0.25rem;
    font-weight: 600;
    text-transform: uppercase;
    font-size: 0.75rem;
  }

  .error-category.ssl_error,
  .error-category.tls_error {
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
  }

  .error-category.dns_error,
  .error-category.hostname_error {
    background: rgba(245, 158, 11, 0.1);
    color: #f59e0b;
  }

  .error-category.timeout_error {
    background: rgba(59, 130, 246, 0.1);
    color: #3b82f6;
  }

  .error-category.connection_error {
    background: rgba(156, 163, 175, 0.1);
    color: #6b7280;
  }

  .error-hint {
    color: var(--primary-color);
    font-style: italic;
    padding: 0.25rem;
    background: rgba(79, 70, 229, 0.05);
    border-radius: 0.25rem;
    border-left: 3px solid var(--primary-color);
    display: block;
    margin-top: 0.25rem;
  }

  .error-actions {
    margin-top: 1.5rem;
  }

  .error-actions .retry-btn {
    padding: 0.625rem 1.5rem;
    background: var(--primary-color);
    color: white;
    border: none;
    border-radius: 0.5rem;
    cursor: pointer;
    font-size: 0.95rem;
    font-weight: 500;
    transition: all 0.2s;
  }

  .error-actions .retry-btn:hover {
    background: var(--primary-hover);
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
  }

  /* Legacy error styles (deprecated - kept for compatibility) */

  .scroll-to-bottom {
    position: absolute;
    bottom: 7rem;
    left: 50%;
    width: 36px;
    height: 36px;
    background: var(--bg-secondary);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
    border-radius: 50%;
    cursor: pointer;
    font-size: 1.25rem;
    font-weight: bold;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    transition: all 0.3s ease;
    z-index: 10;
    animation: fadeInUp 0.3s ease-out;
  }

  .scroll-to-bottom:hover {
    background: var(--bg-tertiary);
    color: var(--primary-color);
    border-color: var(--primary-color);
    transform: translateY(-2px) scale(1.05);
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
  }

  .scroll-to-bottom:active {
    transform: translateY(0) scale(0.98);
    background: var(--bg-tertiary);
    color: var(--primary-color);
  }

  @keyframes fadeInUp {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .no-conversation-prompt {
    padding: 2rem;
    text-align: center;
    color: var(--text-secondary);
    font-size: 1rem;
    opacity: 0.7;
  }

  /* Multi-model cards layout */
  .assistant-messages-grid {
    display: flex;
    gap: 1rem;
    overflow-x: auto;
    scrollbar-width: thin;
    scrollbar-color: var(--border-color) transparent;
    padding-bottom: 0.5rem;
    margin-bottom: 2rem;
  }

  .assistant-messages-grid::-webkit-scrollbar {
    height: 6px;
  }

  .assistant-messages-grid::-webkit-scrollbar-track {
    background: transparent;
  }

  .assistant-messages-grid::-webkit-scrollbar-thumb {
    background: var(--border-color);
    border-radius: 3px;
  }

  .assistant-messages-grid::-webkit-scrollbar-thumb:hover {
    background: var(--text-tertiary);
  }

  .assistant-message-column {
    flex: 0 0 calc(50% - 0.5rem);
    min-width: 300px;
    display: flex;
    flex-direction: column;
  }

  /* Single model card - expand to full width */
  .assistant-messages-grid:has(.assistant-message-column:only-child) .assistant-message-column {
    flex: 0 0 100%;
  }

  /* Tablet styles */
  @media (max-width: 1024px) {
    .messages-container {
      padding: 1.5rem;
    }
  }

  /* Mobile styles */
  @media (max-width: 768px) {
    /* 移动端布局调整：模型选择器固定在顶部 */
    .chat-area {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      display: flex;
      flex-direction: column;
      z-index: 10; /* 确保在背景之上 */
    }

    /* 模型选择器固定在顶部，不随滚动移动 */
    .model-selector-container {
      position: sticky;
      top: 3.5rem; /* 距离顶部56px，给Header留出空间 */
      z-index: 20;
      background: var(--bg-primary);
      border-bottom: 1px solid var(--border-color);
      padding: 0.75rem; /* 恢复默认内边距 */
      gap: 0.5rem; /* 恢复默认间距 */
      flex-shrink: 0;
    }

    /* 消息列表区域可滚动 */
    .messages-container {
      flex: 1;
      overflow-y: auto;
      overflow-x: hidden;
      padding: 1rem;
      background: var(--bg-secondary);
      min-height: 0; /* 重要：让flex子项可以收缩 */
    }

    .messages-container::-webkit-scrollbar {
      width: 4px;
    }

    /* 输入框固定在底部 */
    .input-container {
      position: sticky;
      bottom: 0;
      z-index: 20;
      flex-shrink: 0;
    }

    .welcome h2 {
      font-size: 1.5rem;
    }

    .welcome p {
      font-size: 0.9rem;
    }

    .expand-sidebar-btn {
      width: 36px;
      height: 36px;
    }

    .scroll-to-bottom {
      width: 32px;
      height: 32px;
      font-size: 1.125rem;
    }
  }

  /* Small mobile styles */
  @media (max-width: 480px) {
    .messages-container {
      padding: 0.75rem;
    }

    .welcome h2 {
      font-size: 1.25rem;
    }

    .scroll-to-bottom {
      width: 30px;
      height: 30px;
      font-size: 1rem;
    }
  }
</style>
