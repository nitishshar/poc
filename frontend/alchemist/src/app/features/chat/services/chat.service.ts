import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { v4 as uuidv4 } from 'uuid';

import {
  CHAT_EXAMPLES,
  ChatExample,
  ChatMessage,
  ChatSession,
  ChatState,
  ContentItem,
  EXAMPLE_CONTENT,
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
  private examplesSubject = new BehaviorSubject<ChatExample[]>(CHAT_EXAMPLES);

  messages$ = this.getMessages();
  loading$ = this.getLoadingState();
  sessions$ = this.getSessions();
  currentSession$ = this.getCurrentSessionObservable();
  currentSessionId$ = this.currentSessionIdSubject.asObservable();
  examples$ = this.examplesSubject.asObservable();

  constructor(private chatStorage: ChatStorageService) {
    console.log('Chat service initialized');

    // Log the available examples
    console.log('Chat examples:', CHAT_EXAMPLES);

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

    // Check if this is a special example message
    if (content.toLowerCase().includes('pie chart')) {
      this.processExampleResponse(content);
      return;
    }

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

      // Process the user's request based on content
      if (content.toLowerCase().includes('table')) {
        this.processExampleResponse(content);
      } else if (
        content.toLowerCase().includes('chart') ||
        content.toLowerCase().includes('graph')
      ) {
        this.processExampleResponse(content);
      } else if (
        content.toLowerCase().includes('card') ||
        content.toLowerCase().includes('summary')
      ) {
        this.processExampleResponse(content);
      } else if (
        content.toLowerCase().includes('rich content') ||
        content.toLowerCase().includes('all')
      ) {
        this.addAllExamples();
      } else {
        const botMessage: ChatMessage = {
          content: 'This is a simulated response.',
          isUser: false,
          timestamp: new Date(),
        };

        console.log('Adding bot response:', botMessage);
        this.addMessage(botMessage);
      }
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
    // Create a message with rich content
    const message: ChatMessage = {
      content: contentItems
        .map((c) => (c.type === 'text' ? c.content : ''))
        .join(' '),
      contentItems: contentItems,
      isUser,
      timestamp: new Date(),
    };

    this.addMessage(message);
  }

  // Get the current examples
  getExamples(): ChatExample[] {
    console.log('Getting examples:', this.examplesSubject.value);
    return this.examplesSubject.value;
  }

  // Set new examples
  setExamples(examples: ChatExample[]): void {
    this.examplesSubject.next(examples);
  }

  // Handle when a user selects an example
  handleExampleSelection(example: ChatExample): void {
    console.log('Example selected:', example);

    // If the example has content items, use those to create a rich message
    if (example.contentItems && example.contentItems.length > 0) {
      if (!this.state.value.currentSession) {
        this.createNewChat();
      }

      this.addMessageWithContent(
        this.state.value.currentSession!,
        example.contentItems,
        true
      );

      // Now handle the response based on the example text
      this.processExampleResponse(example.text);
    } else {
      // Otherwise just treat it as a regular text message
      this.sendMessage(example.text);
    }
  }

  // Process example response based on the text
  private processExampleResponse(text: string): void {
    // This would normally be handled by your API, but for demo purposes
    // we'll respond with different content types based on the example text

    // Set loading state
    this.state.next({
      ...this.state.value,
      isLoading: true,
    });

    // Simulate API delay
    setTimeout(() => {
      if (text.toLowerCase().includes('table')) {
        this.addMessageWithContent(
          this.state.value.currentSession!,
          [
            {
              type: 'text',
              content: "Here's a data table example:",
            },
            EXAMPLE_CONTENT['table'],
          ],
          false
        );
      } else if (
        text.toLowerCase().includes('chart') ||
        text.toLowerCase().includes('graph')
      ) {
        if (text.toLowerCase().includes('pie')) {
          this.addMessageWithContent(
            this.state.value.currentSession!,
            [
              {
                type: 'text',
                content: "Here's a pie chart example:",
              },
              EXAMPLE_CONTENT['pieChart'],
            ],
            false
          );
        } else if (text.toLowerCase().includes('line')) {
          this.addMessageWithContent(
            this.state.value.currentSession!,
            [
              {
                type: 'text',
                content: "Here's a line chart example:",
              },
              EXAMPLE_CONTENT['lineChart'],
            ],
            false
          );
        } else {
          this.addMessageWithContent(
            this.state.value.currentSession!,
            [
              {
                type: 'text',
                content: "Here's a bar chart example:",
              },
              EXAMPLE_CONTENT['barChart'],
            ],
            false
          );
        }
      } else if (
        text.toLowerCase().includes('card') ||
        text.toLowerCase().includes('summary')
      ) {
        this.addMessageWithContent(
          this.state.value.currentSession!,
          [
            {
              type: 'text',
              content: "Here's a card example:",
            },
            EXAMPLE_CONTENT['card'],
          ],
          false
        );
      } else if (
        text.toLowerCase().includes('rich content') ||
        text.toLowerCase().includes('all')
      ) {
        this.addAllExamples();
      } else {
        // Default response
        const botMessage: ChatMessage = {
          content: `You asked: "${text}". I'll help you with that!`,
          isUser: false,
          timestamp: new Date(),
        };

        this.addMessage(botMessage);
      }

      // Clear loading state
      this.state.next({
        ...this.state.value,
        isLoading: false,
      });
    }, 1000);
  }

  // Add all examples at once for demo purposes
  addAllExamples(): void {
    if (!this.state.value.currentSession) {
      this.createNewChat();
    }

    const botMessage: ChatMessage = {
      content: 'Here are some examples of rich content:',
      isUser: false,
      timestamp: new Date(),
      contentItems: [
        {
          type: 'text',
          content:
            'Here are some examples of rich content that our chat interface supports:',
        },
        EXAMPLE_CONTENT['table'],
        EXAMPLE_CONTENT['card'],
        EXAMPLE_CONTENT['barChart'],
      ],
    };

    this.addMessage(botMessage);
  }

  // Add an example message with rich content like Gradio
  addExampleMessage(
    type: 'table' | 'card' | 'barChart' | 'lineChart' | 'pieChart'
  ): void {
    if (!this.state.value.currentSession) {
      this.createNewChat();
    }

    // Create text item
    const textItem: ContentItem = {
      type: 'text',
      content: `Here's an example ${type}:`,
    };

    // Get example content based on type
    const exampleItem = EXAMPLE_CONTENT[type];

    // Add message with rich content
    this.addMessageWithContent(
      this.state.value.currentSession!,
      [textItem, exampleItem],
      false
    );
  }
}
