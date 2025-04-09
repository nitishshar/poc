import { SafeHtml } from '@angular/platform-browser';

export interface TableData {
  columns: string[];
  rows: any[];
}

export interface CardData {
  title?: string;
  subtitle?: string;
  content: string;
  image?: string;
}

export type ContentItem =
  | {
      type: 'text' | 'image' | 'card' | 'html';
      content: string | CardData | SafeHtml;
    }
  | {
      type: 'table';
      content: TableData;
    };

export interface Message {
  contents: ContentItem[];
  isUser: boolean;
  timestamp: Date;
}

export interface ChatMessage {
  content: string;
  isUser: boolean;
  timestamp: Date;
}

export interface ChatSession {
  id: string;
  created: Date;
  messages: ChatMessage[];
  lastMessageTime?: Date;
  title?: string;
}

export interface ChatState {
  sessions: ChatSession[];
  currentSession: ChatSession | null;
  isLoading: boolean;
}

export type ContentTypeGuards = {
  isCardContent: (content: any) => content is CardData;
  isTableContent: (content: any) => content is TableData;
};

export interface GraphData {
  type: 'line' | 'bar' | 'pie';
  data: any[];
}

export interface RichChatMessage {
  contents: ContentItem[];
  isUser: boolean;
  timestamp: Date;
}
