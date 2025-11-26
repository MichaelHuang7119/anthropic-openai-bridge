import { authService } from './auth';

export interface ModelChoice {
  providerName: string;
  apiFormat: string;
  model: string;
}

export interface Conversation {
  id: number;
  title: string;
  provider_name: string | null;
  api_format: string | null;
  model: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export interface Message {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  model: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  created_at: string;
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
  private baseUrl = '/api';

  /**
   * Get all conversations for current user
   */
  async getConversations(limit: number = 50, offset: number = 0): Promise<Conversation[]> {
    try {
      const token = authService.getToken();
      if (!token) {
        throw new Error('Not authenticated');
      }

      const response = await fetch(`${this.baseUrl}/conversations?limit=${limit}&offset=${offset}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to fetch conversations' }));
        throw new Error(error.detail || 'Failed to fetch conversations');
      }

      return await response.json();
    } catch (error) {
      console.error('Failed to get conversations:', error);
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
        throw new Error('Not authenticated');
      }

      const response = await fetch(`${this.baseUrl}/conversations/${conversationId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to fetch conversation' }));
        throw new Error(error.detail || 'Failed to fetch conversation');
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
    model: string
  ): Promise<Conversation> {
    try {
      const token = authService.getToken();
      if (!token) {
        throw new Error('Not authenticated');
      }

      const response = await fetch(`${this.baseUrl}/conversations`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          title,
          provider_name: providerName,
          api_format: apiFormat,
          model
        })
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to create conversation' }));
        throw new Error(error.detail || 'Failed to create conversation');
      }

      return await response.json();
    } catch (error) {
      console.error('Failed to create conversation:', error);
      throw error;
    }
  }

  /**
   * Update conversation title
   */
  async updateConversation(conversationId: number, title: string): Promise<Conversation> {
    try {
      const token = authService.getToken();
      if (!token) {
        throw new Error('Not authenticated');
      }

      const response = await fetch(`${this.baseUrl}/conversations/${conversationId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ title })
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to update conversation' }));
        throw new Error(error.detail || 'Failed to update conversation');
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
        throw new Error('Not authenticated');
      }

      const response = await fetch(`${this.baseUrl}/conversations/${conversationId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to delete conversation' }));
        throw new Error(error.detail || 'Failed to delete conversation');
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
    role: 'user' | 'assistant',
    content: string,
    model?: string,
    inputTokens?: number,
    outputTokens?: number
  ): Promise<Message> {
    try {
      const token = authService.getToken();
      if (!token) {
        throw new Error('Not authenticated');
      }

      const params = new URLSearchParams({
        role,
        content
      });

      if (model) params.append('model', model);
      if (inputTokens !== undefined) params.append('input_tokens', inputTokens.toString());
      if (outputTokens !== undefined) params.append('output_tokens', outputTokens.toString());

      const response = await fetch(
        `${this.baseUrl}/conversations/${conversationId}/messages?${params}`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to add message' }));
        throw new Error(error.detail || 'Failed to add message');
      }

      return await response.json();
    } catch (error) {
      console.error(`Failed to add message to conversation ${conversationId}:`, error);
      throw error;
    }
  }

  /**
   * Get messages for a conversation
   */
  async getMessages(conversationId: number, limit?: number): Promise<Message[]> {
    try {
      const token = authService.getToken();
      if (!token) {
        throw new Error('Not authenticated');
      }

      const url = new URL(`${this.baseUrl}/conversations/${conversationId}/messages`);
      if (limit) url.searchParams.append('limit', limit.toString());

      const response = await fetch(url.toString(), {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to fetch messages' }));
        throw new Error(error.detail || 'Failed to fetch messages');
      }

      return await response.json();
    } catch (error) {
      console.error(`Failed to get messages for conversation ${conversationId}:`, error);
      throw error;
    }
  }

  /**
   * Send chat message to AI and get streaming response
   */
  async sendChatMessage(
    conversation: ConversationDetail,
    message: string,
    onStream: (chunk: string) => void,
    onComplete: () => void,
    onError: (error: Error) => void
  ): Promise<void> {
    try {
      const apiKey = authService.getApiKey();
      if (!apiKey) {
        throw new Error('No API key configured');
      }

      if (!conversation.model) {
        throw new Error('No model selected');
      }

      // Prepare messages (all messages from conversation + new message)
      const messages = [
        ...conversation.messages.map(msg => ({
          role: msg.role,
          content: msg.content
        })),
        {
          role: 'user',
          content: message
        }
      ];

      const requestBody = {
        model: conversation.model,
        messages: messages,
        max_tokens: 4096,
        stream: true
      };

      const response = await fetch('/v1/messages', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ error: { message: 'Failed to send message' } }));
        throw new Error(error.error?.message || 'Failed to send message');
      }

      if (!response.body) {
        throw new Error('No response body');
      }

      // Handle streaming response
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          onComplete();
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);

            if (data === '[DONE]') {
              onComplete();
              return;
            }

            try {
              const parsed = JSON.parse(data);

              // Handle different event types
              if (parsed.type === 'content_block_delta' && parsed.delta?.text) {
                onStream(parsed.delta.text);
              } else if (parsed.type === 'message_start' && parsed.message?.usage) {
                // Message started, could track usage here
                console.log('Message started with usage:', parsed.message.usage);
              } else if (parsed.type === 'message_stop') {
                onComplete();
                return;
              }
            } catch (e) {
              console.error('Failed to parse SSE data:', data, e);
            }
          }
        }
      }
    } catch (error) {
      console.error('Failed to send chat message:', error);
      onError(error instanceof Error ? error : new Error(String(error)));
    }
  }

  /**
   * Generate conversation title from first message
   */
  generateTitle(message: string): string {
    // Take first 50 characters, remove newlines, add ellipsis if needed
    const trimmed = message.replace(/\n/g, ' ').trim();
    return trimmed.length > 50 ? trimmed.slice(0, 50) + '...' : trimmed;
  }
}

export const chatService = new ChatService();
