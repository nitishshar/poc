/**
 * Interface representing a chat message within a session
 * Aligns with the FastAPI ChatMessageModel
 */
export interface ChatMessage {
  id?: string;
  text: string;
  role: string;
  timestamp?: string;
  metadata?: Record<string, any>;
}

/**
 * Request model for sending a new chat message
 */
export interface ChatMessageRequest {
  text: string;
}
