import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { v4 as uuidv4 } from 'uuid';

import {
  ChatMessage,
  ChatSession,
  ChatState,
  ContentItem,
} from '../models/chat.types';
import { ChatStorageService } from './chat-storage.service';

@Injectable({
  providedIn: 'root',
})
export class ChatService {
  private state = new BehaviorSubject<ChatState>({
    sessions: [],
    currentSession: null,
    isLoading: false,
  });

  private currentSessionIdSubject = new BehaviorSubject<string | null>(null);

  messages$ = this.getMessages();
  loading$ = this.getLoadingState();
  sessions$ = this.getSessions();
  currentSession$ = this.getCurrentSessionObservable();
  currentSessionId$ = this.currentSessionIdSubject.asObservable();

  constructor(private chatStorage: ChatStorageService) {
    this.loadSessions();
  }

  private loadSessions(): void {
    const sessions = this.chatStorage.loadSessions();
    this.state.next({
      ...this.state.value,
      sessions,
      currentSession: sessions.length > 0 ? sessions[0] : null,
    });

    if (sessions.length > 0) {
      this.currentSessionIdSubject.next(sessions[0].id);
    }
  }

  getState(): Observable<ChatState> {
    return this.state.asObservable();
  }

  private getSessions(): Observable<ChatSession[]> {
    // Return the sessions directly from the state
    return this.state.asObservable().pipe(
      map((state) =>
        state.sessions.map((session) => ({
          ...session,
          title: this.generateSessionTitle(session),
        }))
      )
    );
  }

  private getMessages(): Observable<ChatMessage[]> {
    return this.state
      .asObservable()
      .pipe(map((state) => state.currentSession?.messages || []));
  }

  private getLoadingState(): Observable<boolean> {
    return this.state.asObservable().pipe(map((state) => state.isLoading));
  }

  private getCurrentSessionObservable(): Observable<ChatSession | null> {
    return this.state.asObservable().pipe(map((state) => state.currentSession));
  }

  createNewChat(): void {
    console.log('Creating new chat session');

    // Create new session with welcome message
    const welcomeMessage: ChatMessage = {
      content: 'Welcome! How can I help you today?',
      isUser: false,
      timestamp: new Date(),
    };

    const newSession: ChatSession = {
      id: uuidv4(),
      created: new Date(),
      messages: [welcomeMessage], // Add welcome message
      lastMessageTime: welcomeMessage.timestamp,
    };

    const updatedSessions = [newSession, ...this.state.value.sessions];

    console.log('New session created:', newSession);
    console.log('Updated sessions:', updatedSessions);

    this.state.next({
      ...this.state.value,
      sessions: updatedSessions,
      currentSession: newSession,
    });

    this.currentSessionIdSubject.next(newSession.id);
    this.chatStorage.saveSessions(updatedSessions);
  }

  switchSession(sessionId: string): void {
    const session = this.state.value.sessions.find((s) => s.id === sessionId);
    if (session) {
      this.state.next({
        ...this.state.value,
        currentSession: session,
      });
      this.currentSessionIdSubject.next(session.id);
    }
  }

  async sendMessage(content: string): Promise<void> {
    console.log('Sending message:', content);

    if (!content.trim()) {
      console.log('Message content is empty, not sending');
      return;
    }

    if (!this.state.value.currentSession) {
      console.log('No current session, creating new chat');
      this.createNewChat();
    }

    const userMessage: ChatMessage = {
      content: content.trim(),
      isUser: true,
      timestamp: new Date(),
    };

    console.log('Adding user message:', userMessage);

    // Add user message
    this.addMessage(userMessage);

    // Set loading state
    this.state.next({
      ...this.state.value,
      isLoading: true,
    });

    try {
      console.log('Simulating API response...');
      // TODO: Implement actual API call here
      // For now, simulate a response
      await new Promise((resolve) => setTimeout(resolve, 1000));

      const botMessage: ChatMessage = {
        content: 'This is a simulated response.',
        isUser: false,
        timestamp: new Date(),
      };

      console.log('Adding bot response:', botMessage);
      this.addMessage(botMessage);
    } finally {
      this.state.next({
        ...this.state.value,
        isLoading: false,
      });
    }
  }

  getCurrentSession(): ChatSession | null {
    return this.state.value.currentSession;
  }

  generateSessionTitle(session: ChatSession): string {
    if (session.messages.length === 0) {
      return 'New Chat';
    }
    // Get the first user message as the title
    const firstUserMessage = session.messages.find((m) => m.isUser);
    return firstUserMessage
      ? firstUserMessage.content.substring(0, 20) +
          (firstUserMessage.content.length > 20 ? '...' : '')
      : 'Chat ' + new Date(session.created).toLocaleString();
  }

  addMessage(message: ChatMessage): void {
    if (!this.state.value.currentSession) {
      this.createNewChat();
    }

    const updatedSession: ChatSession = {
      ...this.state.value.currentSession!,
      messages: [...this.state.value.currentSession!.messages, message],
      lastMessageTime: message.timestamp,
    };

    const updatedSessions = this.state.value.sessions.map((s) =>
      s.id === updatedSession.id ? updatedSession : s
    );

    this.state.next({
      ...this.state.value,
      sessions: updatedSessions,
      currentSession: updatedSession,
    });

    this.chatStorage.saveSessions(updatedSessions);
  }

  clearCurrentChat(): void {
    if (!this.state.value.currentSession) return;

    const updatedSession: ChatSession = {
      ...this.state.value.currentSession,
      messages: [],
    };

    const updatedSessions = this.state.value.sessions.map((s) =>
      s.id === updatedSession.id ? updatedSession : s
    );

    this.state.next({
      ...this.state.value,
      sessions: updatedSessions,
      currentSession: updatedSession,
    });

    this.chatStorage.saveSessions(updatedSessions);
  }

  deleteSession(sessionId: string): void {
    const updatedSessions = this.state.value.sessions.filter(
      (s) => s.id !== sessionId
    );
    const currentSession =
      this.state.value.currentSession?.id === sessionId
        ? updatedSessions[0] || null
        : this.state.value.currentSession;

    this.state.next({
      ...this.state.value,
      sessions: updatedSessions,
      currentSession,
    });

    if (currentSession) {
      this.currentSessionIdSubject.next(currentSession.id);
    } else {
      this.currentSessionIdSubject.next(null);
    }

    this.chatStorage.saveSessions(updatedSessions);
  }

  addMessageWithContent(
    session: ChatSession,
    contentItems: ContentItem[],
    isUser: boolean
  ): void {
    // This is a stub method to support the existing component
    const message = {
      content: contentItems
        .map((c) => (c.type === 'text' ? c.content : ''))
        .join(' '),
      isUser,
      timestamp: new Date(),
    };

    this.addMessage(message);
  }
}
