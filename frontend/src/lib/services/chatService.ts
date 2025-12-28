import { authService } from "./auth";
import { getOrCreateSessionId } from "$lib/utils/session";

export interface ModelChoice {
  providerName: string;
  apiFormat: string;
  model: string;
  modelInstanceIndex?: number;
}

export interface Conversation {
  id: number;
  title: string;
  provider_name: string | null;
  api_format: string | null;
  model: string | null;
  last_model: string | null;
  last_provider_name?: string | null;
  last_api_format?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  thinking?: string; // Extended thinking content
  provider_name?: string | null; // Provider used for this message
  api_format?: string | null; // API format used for this message
  model: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  created_at: string;
  parent_message_id?: number | null; // ID of the parent user message for assistant messages
  model_instance_index?: number; // Index of the model instance for multi-model scenarios
  isStreaming?: boolean; // Whether this message is currently streaming
}

export interface ChatState {
  conversations: Conversation[];
  currentConversation: ConversationDetail | null;
  selectedModel: ModelChoice | null;
  isLoading: boolean;
  streamingMessage: string | null;
  error: string | null;
}

class ChatService {
  private baseUrl = "/api";

  /**
   * Get all conversations for current user
   */
  async getConversations(
    limit: number = 50,
    offset: number = 0,
  ): Promise<Conversation[]> {
    try {
      const token = authService.getToken();
      if (!token) {
        throw new Error("Not authenticated");
      }

      const response = await fetch(
        `${this.baseUrl}/conversations?limit=${limit}&offset=${offset}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        },
      );

      // Check for 401 Unauthorized
      if (await authService.checkUnauthorized(response)) {
        throw new Error("Authentication failed - redirected to login");
      }

      if (!response.ok) {
        const error = await response
          .json()
          .catch(() => ({ detail: "Failed to fetch conversations" }));
        throw new Error(error.detail || "Failed to fetch conversations");
      }

      return await response.json();
    } catch (error) {
      console.error("Failed to get conversations:", error);
      throw error;
    }
  }

  /**
   * Get a specific conversation with messages
   */
  async getConversation(conversationId: number): Promise<ConversationDetail> {
    try {
      const token = authService.getToken();
      if (!token) {
        throw new Error("Not authenticated");
      }

      const response = await fetch(
        `${this.baseUrl}/conversations/${conversationId}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        },
      );

      // Check for 401 Unauthorized
      if (await authService.checkUnauthorized(response)) {
        throw new Error("Authentication failed - redirected to login");
      }

      if (!response.ok) {
        const error = await response
          .json()
          .catch(() => ({ detail: "Failed to fetch conversation" }));
        throw new Error(error.detail || "Failed to fetch conversation");
      }

      return await response.json();
    } catch (error) {
      console.error(`Failed to get conversation ${conversationId}:`, error);
      throw error;
    }
  }

  /**
   * Create a new conversation
   */
  async createConversation(
    title: string,
    providerName: string,
    apiFormat: string,
    model: string,
  ): Promise<Conversation> {
    try {
      const token = authService.getToken();
      if (!token) {
        throw new Error("Not authenticated");
      }

      const response = await fetch(`${this.baseUrl}/conversations`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title,
          provider_name: providerName,
          api_format: apiFormat,
          model,
        }),
      });

      // Check for 401 Unauthorized
      if (await authService.checkUnauthorized(response)) {
        throw new Error("Authentication failed - redirected to login");
      }

      if (!response.ok) {
        const error = await response
          .json()
          .catch(() => ({ detail: "Failed to create conversation" }));
        throw new Error(error.detail || "Failed to create conversation");
      }

      return await response.json();
    } catch (error) {
      console.error("Failed to create conversation:", error);
      throw error;
    }
  }

  /**
   * Update conversation title
   */
  async updateConversation(
    conversationId: number,
    title: string,
  ): Promise<Conversation> {
    try {
      const token = authService.getToken();
      if (!token) {
        throw new Error("Not authenticated");
      }

      const response = await fetch(
        `${this.baseUrl}/conversations/${conversationId}`,
        {
          method: "PUT",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ title }),
        },
      );

      // Check for 401 Unauthorized
      if (await authService.checkUnauthorized(response)) {
        throw new Error("Authentication failed - redirected to login");
      }

      if (!response.ok) {
        const error = await response
          .json()
          .catch(() => ({ detail: "Failed to update conversation" }));
        throw new Error(error.detail || "Failed to update conversation");
      }

      return await response.json();
    } catch (error) {
      console.error(`Failed to update conversation ${conversationId}:`, error);
      throw error;
    }
  }

  /**
   * Delete a conversation
   */
  async deleteConversation(conversationId: number): Promise<void> {
    try {
      const token = authService.getToken();
      if (!token) {
        throw new Error("Not authenticated");
      }

      const response = await fetch(
        `${this.baseUrl}/conversations/${conversationId}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      );

      // Check for 401 Unauthorized
      if (await authService.checkUnauthorized(response)) {
        throw new Error("Authentication failed - redirected to login");
      }

      if (!response.ok) {
        const error = await response
          .json()
          .catch(() => ({ detail: "Failed to delete conversation" }));
        throw new Error(error.detail || "Failed to delete conversation");
      }
    } catch (error) {
      console.error(`Failed to delete conversation ${conversationId}:`, error);
      throw error;
    }
  }

  /**
   * Add a message to conversation
   */
  async addMessage(
    conversationId: number,
    role: "user" | "assistant",
    content: string,
    model?: string,
    thinking?: string,
    inputTokens?: number,
    outputTokens?: number,
    providerName?: string,
    apiFormat?: string,
    parentMessageId?: number,
    modelInstanceIndex?: number,
  ): Promise<Message> {
    try {
      const token = authService.getToken();
      if (!token) {
        throw new Error("Not authenticated");
      }

      const requestBody: {
        role: string;
        content: string;
        model?: string;
        thinking?: string;
        input_tokens?: number;
        output_tokens?: number;
        provider_name?: string;
        api_format?: string;
        parent_message_id?: number;
        model_instance_index?: number;
      } = {
        role,
        content,
      };

      if (model) requestBody.model = model;
      if (thinking) requestBody.thinking = thinking;
      if (inputTokens !== undefined) requestBody.input_tokens = inputTokens;
      if (outputTokens !== undefined) requestBody.output_tokens = outputTokens;
      if (providerName !== undefined) requestBody.provider_name = providerName;
      if (apiFormat !== undefined) requestBody.api_format = apiFormat;
      if (parentMessageId !== undefined)
        requestBody.parent_message_id = parentMessageId;
      if (modelInstanceIndex !== undefined)
        requestBody.model_instance_index = modelInstanceIndex;

      const response = await fetch(
        `${this.baseUrl}/conversations/${conversationId}/messages`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(requestBody),
        },
      );

      // Check for 401 Unauthorized
      if (await authService.checkUnauthorized(response)) {
        throw new Error("Authentication failed - redirected to login");
      }

      if (!response.ok) {
        let errorMessage = "Failed to add message";
        try {
          const errorData = await response.json();
          console.error("API Error Response:", errorData);
          errorMessage =
            errorData.detail || errorData.message || JSON.stringify(errorData);
        } catch (e) {
          console.error("Failed to parse error response:", e);
          errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }

      return await response.json();
    } catch (error) {
      console.error(
        `Failed to add message to conversation ${conversationId}:`,
        error,
      );
      throw error;
    }
  }

  /**
   * Get messages for a conversation
   */
  async getMessages(
    conversationId: number,
    limit?: number,
  ): Promise<Message[]> {
    try {
      const token = authService.getToken();
      if (!token) {
        throw new Error("Not authenticated");
      }

      const url = new URL(
        `${this.baseUrl}/conversations/${conversationId}/messages`,
      );
      if (limit) url.searchParams.append("limit", limit.toString());

      const response = await fetch(url.toString(), {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      // Check for 401 Unauthorized
      if (await authService.checkUnauthorized(response)) {
        throw new Error("Authentication failed - redirected to login");
      }

      if (!response.ok) {
        const error = await response
          .json()
          .catch(() => ({ detail: "Failed to fetch messages" }));
        throw new Error(error.detail || "Failed to fetch messages");
      }

      return await response.json();
    } catch (error) {
      console.error(
        `Failed to get messages for conversation ${conversationId}:`,
        error,
      );
      throw error;
    }
  }

  /**
   * Send chat message to AI and get streaming response
   */
  async sendChatMessage(
    conversation: ConversationDetail,
    message: string,
    onStream: (chunk: string, thinking?: string) => void,
    onComplete: (usage?: {
      input_tokens: number;
      output_tokens: number;
    }) => void,
    onError: (error: Error) => void,
    abortController?: AbortController,
  ): Promise<{ messageId: string }> {
    // Generate unique message ID for this request
    const messageId = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    console.log(
      `sendChatMessage: Created message ID ${messageId} for conversation ${conversation.id}`,
    );

    try {
      const token = authService.getAuthHeaders().Authorization;
      if (!token) {
        throw new Error("Not authenticated");
      }

      if (!conversation.model) {
        throw new Error("No model selected");
      }

      // Prepare messages (all messages from conversation + new message)
      // Filter out messages with missing content
      console.log(
        "chatService: All conversation messages:",
        conversation.messages,
      );
      const filteredMessages = conversation.messages.filter(
        (msg) => msg.content && msg.content.trim(),
      );
      console.log("chatService: Filtered messages:", filteredMessages);

      // Check if the new message is already in the conversation.messages
      // This happens when the message was already added to the local state (e.g., from ChatArea)
      // Use message ID comparison to avoid false positives from message content alone
      const isMessageAlreadyAdded = filteredMessages.some(
        (msg) => msg.role === "user" && msg.content === message,
      );

      console.log("=== DUPLICATE CHECK DEBUG ===");
      console.log("chatService: New message to send:", message);
      console.log(
        "chatService: Existing messages count:",
        filteredMessages.length,
      );
      console.log("chatService: isMessageAlreadyAdded:", isMessageAlreadyAdded);
      filteredMessages.forEach((msg, idx) => {
        console.log(`  [${idx}] role: ${msg.role}, content: "${msg.content}"`);
      });
      console.log("=== END DUPLICATE CHECK DEBUG ===");

      // Build the messages array for the API
      const messages = filteredMessages.map((msg) => ({
        role: msg.role,
        content: msg.content,
      }));

      // Only add the new message if it's not already in the conversation
      if (!isMessageAlreadyAdded) {
        messages.push({
          role: "user",
          content: message,
        });
      } else {
        console.log(
          "ChatService: Message already in conversation, skipping duplicate add",
        );
      }

      console.log("chatService: Final messages to send:", messages);

      const requestBody = {
        model: conversation.model,
        messages: messages,
        max_tokens: 4096,
        stream: true,
      };

      // Add provider and api_format to headers if available
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
        ...authService.getAuthHeaders(),
      };

      // Add request identifiers for strict isolation
      const sessionId = getOrCreateSessionId();
      headers["X-Session-Id"] = sessionId;
      headers["X-Chat-Id"] = String(conversation.id); // chat_id for conversation-level isolation
      headers["X-Message-Id"] = messageId; // message_id for message-level isolation

      if (conversation.provider_name) {
        headers["X-Provider-Name"] = conversation.provider_name;
      }
      if (conversation.api_format) {
        headers["X-API-Format"] = conversation.api_format;
      }

      console.log("chatService: Request headers:", headers);
      console.log("chatService: Request body:", requestBody);
      console.log(
        "chatService: Session ID:",
        sessionId,
        "Chat ID:",
        conversation.id,
        "Message ID:",
        messageId,
      );

      const response = await fetch("/v1/messages", {
        method: "POST",
        headers: headers,
        body: JSON.stringify(requestBody),
        signal: abortController?.signal,
      });

      if (!response.ok) {
        let errorInfo: any = null;
        let errorMessage = "Failed to send message";

        try {
          errorInfo = await response.json();

          // Check if the detail field is a JSON string (structured error response)
          if (typeof errorInfo.detail === "string") {
            try {
              // Try to parse the detail as JSON (new structured error format)
              const parsedDetail = JSON.parse(errorInfo.detail);

              // Extract all available fields
              // eslint-disable-next-line @typescript-eslint/no-unused-vars
              const {
                message,
                type,
                status_code: _status_code,
                request_id: _request_id,
                provider: _provider,
                model: _model,
                provider_status_code,
                provider_url: _provider_url,
              } = parsedDetail;

              // Build comprehensive error message
              if (message) {
                errorMessage = message;

                // Add provider status code if available (e.g., "403 Forbidden")
                if (provider_status_code) {
                  errorMessage += ` [Provider Status: ${provider_status_code}]`;
                }

                // Add error type for debugging
                if (type) {
                  errorMessage += ` (${type})`;
                }
              }

              // Store all parsed details for frontend display
              errorInfo = {
                ...errorInfo,
                ...parsedDetail,
                // Override detail with parsed JSON
                detail: parsedDetail,
              };
            } catch (jsonParseError) {
              // If JSON parsing fails, treat as plain string
              console.error(
                "Failed to parse error detail as JSON:",
                jsonParseError,
              );
              errorMessage = errorInfo.detail;
            }
          } else {
            // Fallback to original extraction logic for non-JSON errors
            const backendMessage =
              errorInfo.error?.message || errorInfo.message || errorInfo.detail;
            const errorType = errorInfo.error?.type || errorInfo.type;
            const errorCode = errorInfo.error?.code || errorInfo.code;

            if (backendMessage) {
              errorMessage = backendMessage;
              if (errorType || errorCode) {
                errorMessage += ` (${errorType || errorCode})`;
              }
            }
          }

          // Log detailed error for debugging
          console.error("Backend error response:", {
            status: response.status,
            statusText: response.statusText,
            error: errorInfo,
          });
        } catch (parseError) {
          console.error("Failed to parse error response:", parseError);
          errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        }

        // Create detailed error object
        const error = new Error(errorMessage) as Error & {
          status?: number;
          statusText?: string;
          details?: any;
        };
        error.status = response.status;
        error.statusText = response.statusText;
        error.details = errorInfo;

        throw error;
      }

      if (!response.body) {
        throw new Error("No response body");
      }

      // Handle streaming response
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let buffer = "";
      let currentThinking = ""; // Accumulate thinking content
      let usage: { input_tokens: number; output_tokens: number } | undefined;
      let hasCompleted = false; // Track if onComplete has already been called

      try {
        // eslint-disable-next-line no-constant-condition
        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            onComplete(usage);
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n\n");
          buffer = lines.pop() || "";

          for (const block of lines) {
            if (!block.trim()) continue;

            // Parse SSE format: event: type\ndata: json
            const eventLines = block.split("\n");
            let eventData = null;

            for (const line of eventLines) {
              if (line.startsWith("data: ")) {
                eventData = line.slice(6).trim();
              }
            }

            // If no explicit event type, check if data starts with "data: "
            if (!eventData && block.startsWith("data: ")) {
              eventData = block.slice(6).trim();
            }

            if (!eventData) continue;

            if (eventData === "[DONE]") {
              if (!hasCompleted) {
                onComplete(usage);
                hasCompleted = true;
              }
              break;
            }

            try {
              const parsed = JSON.parse(eventData);

              // Handle different event types
              if (parsed.type === "content_block_delta") {
                // Handle thinking content
                if (
                  parsed.delta?.type === "thinking_delta" &&
                  parsed.delta?.thinking
                ) {
                  currentThinking += parsed.delta.thinking;
                  // Send both empty text and thinking update
                  onStream("", currentThinking);
                }
                // Handle regular text content
                else if (parsed.delta?.text) {
                  onStream(parsed.delta.text, currentThinking);
                }
              } else if (parsed.type === "content_block_start") {
                // Reset thinking when a new thinking block starts
                if (parsed.content_block?.type === "thinking") {
                  currentThinking = "";
                }
              } else if (
                parsed.type === "message_start" &&
                parsed.message?.usage
              ) {
                // Capture usage information
                usage = {
                  input_tokens: parsed.message.usage.input_tokens || 0,
                  output_tokens: parsed.message.usage.output_tokens || 0,
                };
                console.log("Message started with usage:", usage);
              } else if (parsed.type === "message_delta" && parsed.usage) {
                // Update usage information if provided in delta
                usage = {
                  input_tokens:
                    parsed.usage.input_tokens || usage?.input_tokens || 0,
                  output_tokens:
                    parsed.usage.output_tokens || usage?.output_tokens || 0,
                };
                console.log("Usage updated:", usage);
              } else if (parsed.type === "message_stop") {
                if (!hasCompleted) {
                  onComplete(usage);
                  hasCompleted = true;
                }
                break;
              } else if (parsed.type === "ping") {
                // Ignore ping events
                continue;
              } else if (parsed.type === "error") {
                // Handle streaming errors from backend
                const errorInfo = parsed.error;

                // Build comprehensive error message
                let errorMessage =
                  errorInfo?.message || "Unknown error from provider";

                // Add provider name if available
                if (errorInfo?.provider) {
                  errorMessage = `${errorInfo.provider}: ${errorMessage}`;
                }

                // Add error type if available
                if (errorInfo?.type) {
                  errorMessage += ` (${errorInfo.type})`;
                }

                // Log detailed error for debugging
                console.error("Streaming error from backend:", errorInfo);

                // Create detailed error object
                const error = new Error(errorMessage) as Error & {
                  status?: number;
                  statusText?: string;
                  details?: any;
                };
                error.status = 503; // Service Unavailable
                error.statusText = "Provider Error";
                error.details = errorInfo;

                // Call onError callback to handle the error
                onError(error);
                break;
              }
            } catch (e) {
              console.error("Failed to parse SSE data:", eventData, e);
            }
          }
        }
      } catch (streamError) {
        console.error("Error reading stream:", streamError);
        onError(
          streamError instanceof Error
            ? streamError
            : new Error(String(streamError)),
        );
        throw streamError;
      }

      // Return message ID for tracking
      return { messageId };
    } catch (error) {
      console.error("Failed to send chat message:", error);
      onError(error instanceof Error ? error : new Error(String(error)));
      throw error;
    } finally {
      // Cleanup if needed
      if (abortController) {
        // AbortController will be handled by the caller
      }
    }
  }

  /**
   * Generate conversation title from first message
   */
  generateTitle(message: string): string {
    // Take first 50 characters, remove newlines, add ellipsis if needed
    const trimmed = message.replace(/\n/g, " ").trim();
    return trimmed.length > 50 ? trimmed.slice(0, 50) + "..." : trimmed;
  }
}

export const chatService = new ChatService();
