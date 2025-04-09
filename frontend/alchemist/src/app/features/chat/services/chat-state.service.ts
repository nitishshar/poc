import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { v4 as uuidv4 } from 'uuid';
import { ChatMessage, ChatSession, ChatState } from '../models/chat.types';
import { ChatStorageService } from './chat-storage.service';

@Injectable({
  providedIn: 'root',
})
export class ChatStateService {
  private state = new BehaviorSubject<ChatState>({
    sessions: [],
    currentSession: null,
    isLoading: false,
  });

  constructor(private chatStorage: ChatStorageService) {
    this.loadSavedSessions();
  }

  private loadSavedSessions(): void {
    const sessions = this.chatStorage.loadSessions();
    this.state.next({
      ...this.state.value,
      sessions,
      currentSession: sessions.length > 0 ? sessions[0] : null,
    });
  }

  getState(): Observable<ChatState> {
    return this.state.asObservable();
  }

  createNewSession(): void {
    const newSession: ChatSession = {
      id: uuidv4(),
      created: new Date(),
      messages: [],
    };

    const updatedSessions = [newSession, ...this.state.value.sessions];

    this.state.next({
      ...this.state.value,
      sessions: updatedSessions,
      currentSession: newSession,
    });

    this.chatStorage.saveSessions(updatedSessions);
  }

  setCurrentSession(sessionId: string): void {
    const session = this.state.value.sessions.find((s) => s.id === sessionId);
    if (session) {
      this.state.next({
        ...this.state.value,
        currentSession: session,
      });
    }
  }

  addMessage(message: Omit<ChatMessage, 'timestamp'>): void {
    if (!this.state.value.currentSession) {
      this.createNewSession();
    }

    const newMessage: ChatMessage = {
      ...message,
      timestamp: new Date(),
    };

    const currentSession = this.state.value.currentSession!;
    const updatedSession: ChatSession = {
      ...currentSession,
      messages: [...currentSession.messages, newMessage],
      lastMessageTime: newMessage.timestamp,
    };

    const updatedSessions = this.state.value.sessions.map((session) =>
      session.id === updatedSession.id ? updatedSession : session
    );

    this.state.next({
      ...this.state.value,
      sessions: updatedSessions,
      currentSession: updatedSession,
    });

    this.chatStorage.saveSessions(updatedSessions);
  }

  setLoading(isLoading: boolean): void {
    this.state.next({
      ...this.state.value,
      isLoading,
    });
  }

  clearCurrentSession(): void {
    if (!this.state.value.currentSession) return;

    const updatedSessions = this.state.value.sessions.filter(
      (session) => session.id !== this.state.value.currentSession?.id
    );

    this.state.next({
      ...this.state.value,
      sessions: updatedSessions,
      currentSession: updatedSessions.length > 0 ? updatedSessions[0] : null,
    });

    this.chatStorage.saveSessions(updatedSessions);
  }

  clearAllSessions(): void {
    this.state.next({
      sessions: [],
      currentSession: null,
      isLoading: false,
    });

    this.chatStorage.clearSessions();
  }
}
