import { ChatMessage } from './chat-message.model';

/**
 * Interface representing a chat session
 * Aligns with the FastAPI ChatSessionModel
 */
export interface ChatSession {
  id?: string;
  name?: string;
  document_id?: string;
  document_ids: string[];
  messages: ChatMessage[];
  created_at?: string;
  updated_at?: string;
  chat_mode?: string;
  llm_provider?: string;
  llm_model?: string;
}

/**
 * Request model for creating a new chat session
 */
export interface ChatSessionRequest {
  name?: string;
  document_id?: string;
  document_ids?: string[];
  chat_mode?: string;
  llm_provider?: string;
  llm_model?: string;
}

/**
 * Interface for document update operations in chat sessions
 */
export interface DocumentUpdateRequest {
  document_id: string;
}
