import { Injectable } from '@angular/core';
import { ChatSession } from '../models/chat.types';

@Injectable({
  providedIn: 'root',
})
export class ChatStorageService {
  private readonly STORAGE_KEY = 'chat_sessions';

  constructor() {}

  saveSessions(sessions: ChatSession[]): void {
    const serializedSessions = sessions.map((session) => ({
      ...session,
      created: session.created.toISOString(),
      lastMessageTime: session.lastMessageTime?.toISOString(),
      messages: session.messages.map((msg) => ({
        ...msg,
        timestamp: msg.timestamp.toISOString(),
      })),
    }));
    localStorage.setItem(this.STORAGE_KEY, JSON.stringify(serializedSessions));
  }

  loadSessions(): ChatSession[] {
    const storedSessions = localStorage.getItem(this.STORAGE_KEY);
    if (!storedSessions) {
      return [];
    }

    try {
      const parsedSessions = JSON.parse(storedSessions);
      return parsedSessions.map((session: any) => ({
        ...session,
        created: new Date(session.created),
        lastMessageTime: session.lastMessageTime
          ? new Date(session.lastMessageTime)
          : undefined,
        messages: session.messages.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp),
        })),
      }));
    } catch (error) {
      console.error('Error loading chat sessions:', error);
      return [];
    }
  }

  clearSessions(): void {
    localStorage.removeItem(this.STORAGE_KEY);
  }
}
