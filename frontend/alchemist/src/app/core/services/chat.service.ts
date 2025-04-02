import { HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, tap } from 'rxjs';

import { ChatMessage } from '../models/chat-message.model';
import { ChatSession, ChatSessionRequest } from '../models/chat-session.model';
import { ApiService } from './api.service';
import { WebsocketService } from './websocket.service';

@Injectable({
  providedIn: 'root',
})
export class ChatService {
  private chatSessionsSubject = new BehaviorSubject<ChatSession[]>([]);
  private currentSessionSubject = new BehaviorSubject<ChatSession | null>(null);

  constructor(
    private apiService: ApiService,
    private websocketService: WebsocketService
  ) {}

  /**
   * Get all chat sessions
   * @returns Observable of chat sessions
   */
  getAllSessions(): Observable<ChatSession[]> {
    return this.apiService.get<ChatSession[]>('/sessions').pipe(
      tap((sessions) => {
        this.chatSessionsSubject.next(sessions);
      })
    );
  }

  /**
   * Get chat sessions as BehaviorSubject
   * @returns BehaviorSubject of chat sessions
   */
  getChatSessionsSubject(): BehaviorSubject<ChatSession[]> {
    return this.chatSessionsSubject;
  }

  /**
   * Get current session as BehaviorSubject
   * @returns BehaviorSubject of current session
   */
  getCurrentSessionSubject(): BehaviorSubject<ChatSession | null> {
    return this.currentSessionSubject;
  }

  /**
   * Get a specific chat session by ID
   * @param sessionId Chat session ID
   * @returns Observable of chat session
   */
  getSession(sessionId: string): Observable<ChatSession> {
    return this.apiService.get<ChatSession>(`/sessions/${sessionId}`).pipe(
      tap((session) => {
        this.currentSessionSubject.next(session);
      })
    );
  }

  /**
   * Create a new chat session
   * @param sessionData Session data
   * @returns Observable of created chat session
   */
  createSession(sessionData: ChatSessionRequest): Observable<ChatSession> {
    return this.apiService.post<ChatSession>('/sessions', sessionData).pipe(
      tap((newSession) => {
        const currentSessions = this.chatSessionsSubject.value;
        this.chatSessionsSubject.next([...currentSessions, newSession]);
        this.currentSessionSubject.next(newSession);
      })
    );
  }

  /**
   * Delete a chat session
   * @param sessionId Chat session ID
   * @returns Observable of delete response
   */
  deleteSession(sessionId: string): Observable<ChatSession> {
    return this.apiService.delete<ChatSession>(`/sessions/${sessionId}`).pipe(
      tap(() => {
        const currentSessions = this.chatSessionsSubject.value;
        const updatedSessions = currentSessions.filter(
          (session) => session.id !== sessionId
        );
        this.chatSessionsSubject.next(updatedSessions);

        const currentSession = this.currentSessionSubject.value;
        if (currentSession && currentSession.id === sessionId) {
          this.currentSessionSubject.next(null);
        }
      })
    );
  }

  /**
   * Send a message to a chat session
   * @param sessionId Chat session ID
   * @param message Message text
   * @param contextWindow Number of previous messages to include as context
   * @returns Observable of updated chat session
   */
  sendMessage(
    sessionId: string,
    message: string,
    contextWindow: number = 4
  ): Observable<ChatSession> {
    const messageRequest: ChatMessageRequest = { text: message };
    let params = new HttpParams().set(
      'context_window',
      contextWindow.toString()
    );

    return this.apiService
      .post<ChatSession>(`/sessions/${sessionId}/messages`, messageRequest, {
        params,
      })
      .pipe(
        tap((updatedSession) => {
          this.currentSessionSubject.next(updatedSession);

          // Update the session in the sessions list
          const currentSessions = this.chatSessionsSubject.value;
          const updatedSessions = currentSessions.map((session) =>
            session.id === sessionId ? updatedSession : session
          );
          this.chatSessionsSubject.next(updatedSessions);
        })
      );
  }

  /**
   * Get messages from a chat session
   * @param sessionId Chat session ID
   * @param limit Maximum number of messages to return
   * @returns Observable of chat messages
   */
  getMessages(
    sessionId: string,
    limit: number = 50
  ): Observable<ChatMessage[]> {
    let params = new HttpParams().set('limit', limit.toString());
    return this.apiService.get<ChatMessage[]>(
      `/sessions/${sessionId}/messages`,
      { params }
    );
  }

  /**
   * Connect to WebSocket for real-time chat
   * @param sessionId Chat session ID
   * @returns WebSocket subject
   */
  connectToWebSocket(sessionId: string): Observable<boolean> {
    return this.websocketService.connect(`/chat/${sessionId}`);
  }

  /**
   * Add a document to a chat session
   * @param sessionId Chat session ID
   * @param documentId Document ID
   * @returns Observable of updated chat session
   */
  addDocumentToSession(
    sessionId: string,
    documentId: string
  ): Observable<ChatSession> {
    return this.apiService
      .post<ChatSession>(`/sessions/${sessionId}/documents`, {
        document_id: documentId,
      })
      .pipe(
        tap((updatedSession) => {
          this.currentSessionSubject.next(updatedSession);

          // Update the session in the sessions list
          const currentSessions = this.chatSessionsSubject.value;
          const updatedSessions = currentSessions.map((session) =>
            session.id === sessionId ? updatedSession : session
          );
          this.chatSessionsSubject.next(updatedSessions);
        })
      );
  }

  /**
   * Remove a document from a chat session
   * @param sessionId Chat session ID
   * @param documentId Document ID
   * @returns Observable of updated chat session
   */
  removeDocumentFromSession(
    sessionId: string,
    documentId: string
  ): Observable<ChatSession> {
    return this.apiService
      .delete<ChatSession>(`/sessions/${sessionId}/documents/${documentId}`)
      .pipe(
        tap((updatedSession) => {
          this.currentSessionSubject.next(updatedSession);

          // Update the session in the sessions list
          const currentSessions = this.chatSessionsSubject.value;
          const updatedSessions = currentSessions.map((session) =>
            session.id === sessionId ? updatedSession : session
          );
          this.chatSessionsSubject.next(updatedSessions);
        })
      );
  }
}
