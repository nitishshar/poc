import { CommonModule } from '@angular/common';
import {
  Component,
  ElementRef,
  Inject,
  OnInit,
  ViewChild,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatListModule } from '@angular/material/list';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ThemeService } from '../../../../core/services/theme.service';

interface Message {
  content: string;
  isUser: boolean;
  timestamp: Date;
}

interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  lastMessageTime: Date;
}

@Component({
  selector: 'app-chat-interface',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatIconModule,
    MatInputModule,
    MatListModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
  ],
  template: `
    <div class="chat-container glass-effect">
      <div class="chat-sidebar">
        <div class="sidebar-header">
          <h3>Chat History</h3>
          <button
            mat-icon-button
            (click)="createNewChat()"
            matTooltip="New chat"
          >
            <mat-icon>add</mat-icon>
          </button>
        </div>
        <mat-nav-list class="chat-history">
          <mat-list-item
            *ngFor="let session of chatSessions"
            [class.active]="session.id === currentSessionId"
            (click)="switchSession(session.id)"
          >
            <div class="session-item">
              <div class="session-title">{{ session.title }}</div>
              <div class="session-time">
                {{ session.lastMessageTime | date : 'shortTime' }}
              </div>
            </div>
            <button
              mat-icon-button
              (click)="deleteSession(session.id, $event)"
              matTooltip="Delete chat"
            >
              <mat-icon>delete</mat-icon>
            </button>
          </mat-list-item>
        </mat-nav-list>
      </div>

      <div class="chat-main">
        <div class="chat-header">
          <h2>{{ getCurrentSession()?.title || 'New Chat' }}</h2>
          <div class="chat-actions">
            <button
              mat-icon-button
              (click)="clearCurrentChat()"
              matTooltip="Clear chat"
            >
              <mat-icon>delete</mat-icon>
            </button>
          </div>
        </div>

        <div class="chat-messages" #chatMessages>
          <div
            *ngFor="let message of getCurrentSession()?.messages || []"
            class="message-container"
            [class.user]="message.isUser"
          >
            <div class="message glass-effect">
              <div class="message-content">{{ message.content }}</div>
              <div class="message-timestamp">
                {{ message.timestamp | date : 'shortTime' }}
              </div>
            </div>
          </div>
          <div *ngIf="isLoading" class="loading-container">
            <mat-progress-spinner
              diameter="24"
              mode="indeterminate"
              color="primary"
            ></mat-progress-spinner>
          </div>
        </div>

        <div class="chat-input-container">
          <mat-form-field class="chat-input">
            <mat-label>Type your message</mat-label>
            <input
              matInput
              [(ngModel)]="userInput"
              (keyup.enter)="sendMessage()"
              placeholder="Type your message..."
            />
            <button mat-icon-button matSuffix (click)="sendMessage()">
              <mat-icon>send</mat-icon>
            </button>
          </mat-form-field>
        </div>
      </div>
    </div>
  `,
  styles: [
    `
      .chat-container {
        display: flex;
        height: 100%;
        min-height: 500px;
        border-radius: var(--border-radius);
        overflow: hidden;
      }

      .chat-sidebar {
        width: 240px;
        border-right: var(--glass-border);
        background-color: var(--glass-background);
        backdrop-filter: blur(var(--blur-amount));
        -webkit-backdrop-filter: blur(var(--blur-amount));
        display: flex;
        flex-direction: column;
      }

      .sidebar-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px;
        height: 40px;
        border-bottom: var(--glass-border);
        background-color: var(--glass-background);
        backdrop-filter: blur(var(--blur-amount));
        -webkit-backdrop-filter: blur(var(--blur-amount));
      }

      .sidebar-header h3 {
        margin: 0;
        font-size: 14px;
        font-weight: 500;
        color: var(--text-color);
      }

      .chat-history {
        flex: 1;
        overflow-y: auto;
        padding: 2px 0;
      }

      .chat-history::-webkit-scrollbar {
        width: 4px;
      }

      .chat-history::-webkit-scrollbar-track {
        background: transparent;
      }

      .chat-history::-webkit-scrollbar-thumb {
        background: var(--primary-color);
        border-radius: 2px;
      }

      .session-item {
        flex: 1;
        display: flex;
        flex-direction: row;
        justify-content: space-between;
        align-items: center;
        gap: 8px;
        padding: 0;
      }

      .session-title {
        font-size: 12px;
        font-weight: 400;
        color: var(--text-color);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        line-height: 1.2;
        flex: 1;
      }

      .session-time {
        font-size: 10px;
        color: var(--secondary-text-color);
        opacity: 0.7;
        white-space: nowrap;
      }

      .chat-main {
        flex: 1;
        display: flex;
        flex-direction: column;
        overflow: hidden;
      }

      .chat-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px;
        border-bottom: var(--glass-border);
        background-color: var(--glass-background);
        backdrop-filter: blur(var(--blur-amount));
        -webkit-backdrop-filter: blur(var(--blur-amount));
      }

      .chat-header h2 {
        margin: 0;
        font-size: 20px;
        font-weight: 500;
        color: var(--text-color);
      }

      .chat-actions {
        display: flex;
        gap: 8px;
      }

      .chat-messages {
        flex: 1;
        overflow-y: auto;
        padding: 16px;
        display: flex;
        flex-direction: column;
        gap: 16px;
        background-color: var(--background-color);
      }

      .message-container {
        display: flex;
        flex-direction: column;
        max-width: 80%;
      }

      .message-container.user {
        align-items: flex-end;
      }

      .message {
        padding: 12px 16px;
        border-radius: var(--border-radius);
        background-color: var(--glass-card-background);
        backdrop-filter: blur(var(--blur-amount));
        -webkit-backdrop-filter: blur(var(--blur-amount));
        border: var(--glass-border);
        box-shadow: var(--card-shadow);
      }

      .message-container.user .message {
        background-color: var(--primary-color);
        color: white;
      }

      .message-content {
        font-size: 14px;
        line-height: 1.5;
        word-wrap: break-word;
      }

      .message-timestamp {
        font-size: 11px;
        opacity: 0.7;
        margin-top: 4px;
        text-align: right;
      }

      .chat-input-container {
        padding: 16px;
        border-top: var(--glass-border);
        background-color: var(--glass-background);
        backdrop-filter: blur(var(--blur-amount));
        -webkit-backdrop-filter: blur(var(--blur-amount));
      }

      .chat-input {
        width: 100%;
      }

      .loading-container {
        display: flex;
        justify-content: center;
        padding: 16px;
      }

      /* Custom scrollbar for chat messages */
      .chat-messages::-webkit-scrollbar {
        width: 8px;
      }

      .chat-messages::-webkit-scrollbar-track {
        background: var(--background-lighter);
      }

      .chat-messages::-webkit-scrollbar-thumb {
        background: var(--primary-color);
        border-radius: 4px;
      }

      /* Material list overrides */
      ::ng-deep .mat-mdc-list-item {
        height: 32px !important;
        min-height: 32px !important;
        padding: 0 8px !important;
        margin: 1px 2px !important;
        border-radius: calc(var(--border-radius) * 0.5);
        transition: all 0.2s ease-in-out;
      }

      ::ng-deep .mat-mdc-list-item:hover {
        background-color: var(--glass-card-background);
        backdrop-filter: blur(var(--blur-amount));
        -webkit-backdrop-filter: blur(var(--blur-amount));
      }

      ::ng-deep .mat-mdc-list-item.active {
        background-color: var(--primary-color);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
      }

      ::ng-deep .mat-mdc-list-item.active .session-title {
        color: white;
        font-weight: 500;
      }

      ::ng-deep .mat-mdc-list-item.active .session-time {
        color: rgba(255, 255, 255, 0.9);
      }

      ::ng-deep .mat-mdc-list-item .mat-icon {
        font-size: 14px;
        width: 14px;
        height: 14px;
        opacity: 0;
        transition: opacity 0.2s ease-in-out;
        margin-left: 4px;
      }

      ::ng-deep .mat-mdc-list-item:hover .mat-icon {
        opacity: 0.7;
      }

      ::ng-deep .mat-mdc-list-item .mat-icon:hover {
        opacity: 1;
      }

      ::ng-deep .mat-mdc-list-item.active .mat-icon {
        color: white;
        opacity: 0.9;
      }

      ::ng-deep .mat-mdc-list-item.active .mat-icon:hover {
        opacity: 1;
      }

      ::ng-deep .mat-mdc-list-item .mat-mdc-button-touch-target {
        height: 32px !important;
      }

      ::ng-deep .mat-mdc-list-item .mdc-list-item__primary-text {
        display: flex;
        align-items: center;
      }

      /* Material form field overrides */
      ::ng-deep .mat-mdc-form-field {
        width: 100%;
      }

      ::ng-deep .mat-mdc-form-field-subscript-wrapper {
        display: none;
      }

      ::ng-deep .mat-mdc-form-field-infix {
        padding-top: 8px;
        padding-bottom: 8px;
      }

      ::ng-deep .mat-mdc-text-field-wrapper {
        background-color: var(--glass-card-background);
        backdrop-filter: blur(var(--blur-amount));
        -webkit-backdrop-filter: blur(var(--blur-amount));
        border: var(--glass-border);
        border-radius: var(--border-radius);
      }

      ::ng-deep .mat-mdc-form-field-focus-overlay {
        background-color: transparent;
      }

      ::ng-deep .mat-mdc-form-field:hover .mat-mdc-form-field-focus-overlay {
        opacity: 0;
      }

      ::ng-deep .mdc-text-field--filled:not(.mdc-text-field--disabled) {
        background-color: transparent;
      }

      ::ng-deep
        .mdc-text-field--filled:not(.mdc-text-field--disabled)
        .mdc-line-ripple::before {
        border-bottom-color: var(--primary-color);
      }

      ::ng-deep
        .mdc-text-field--filled:not(.mdc-text-field--disabled)
        .mdc-line-ripple::after {
        border-bottom-color: var(--primary-color);
      }

      ::ng-deep
        .mat-mdc-form-field.mat-focused
        .mat-mdc-form-field-focus-overlay {
        opacity: 0;
      }

      ::ng-deep .mat-mdc-form-field .mat-mdc-floating-label {
        color: var(--text-color);
      }

      ::ng-deep .mat-mdc-form-field.mat-focused .mat-mdc-floating-label {
        color: var(--primary-color);
      }

      ::ng-deep .mat-mdc-input-element {
        color: var(--text-color);
      }

      ::ng-deep .mat-mdc-form-field-icon-suffix {
        color: var(--text-color);
      }

      ::ng-deep .mat-mdc-form-field-icon-suffix:hover {
        color: var(--primary-color);
      }
    `,
  ],
})
export class ChatInterfaceComponent implements OnInit {
  @ViewChild('chatMessages') private chatMessages!: ElementRef;

  chatSessions: ChatSession[] = [];
  currentSessionId: string = '';
  userInput = '';
  isLoading = false;

  constructor(@Inject(ThemeService) private themeService: ThemeService) {}

  ngOnInit(): void {
    this.loadSessions();
    if (this.chatSessions.length === 0) {
      this.createNewChat();
    } else {
      this.currentSessionId = this.chatSessions[0].id;
    }
  }

  createNewChat(): void {
    const newSession: ChatSession = {
      id: this.generateId(),
      title: 'New Chat',
      messages: [],
      lastMessageTime: new Date(),
    };
    this.chatSessions.unshift(newSession);
    this.currentSessionId = newSession.id;
    this.saveSessions();
  }

  switchSession(sessionId: string): void {
    this.currentSessionId = sessionId;
  }

  deleteSession(sessionId: string, event: Event): void {
    event.stopPropagation();
    const index = this.chatSessions.findIndex((s) => s.id === sessionId);
    if (index !== -1) {
      this.chatSessions.splice(index, 1);
      if (this.currentSessionId === sessionId) {
        this.currentSessionId = this.chatSessions[0]?.id || '';
        if (!this.currentSessionId) {
          this.createNewChat();
        }
      }
      this.saveSessions();
    }
  }

  getCurrentSession(): ChatSession | undefined {
    return this.chatSessions.find((s) => s.id === this.currentSessionId);
  }

  sendMessage(): void {
    if (!this.userInput.trim() || !this.currentSessionId) return;

    const currentSession = this.getCurrentSession();
    if (!currentSession) return;

    // Add user message
    this.addMessage(currentSession, this.userInput, true);
    this.userInput = '';

    // Simulate loading state
    this.isLoading = true;

    // Scroll to bottom
    setTimeout(() => {
      this.scrollToBottom();
    }, 100);

    // Simulate response (replace with actual API call)
    setTimeout(() => {
      this.addMessage(
        currentSession,
        'This is a simulated response. Replace with actual API call.',
        false
      );
      this.isLoading = false;
      this.scrollToBottom();
      this.saveSessions();
    }, 1000);
  }

  clearCurrentChat(): void {
    const currentSession = this.getCurrentSession();
    if (currentSession) {
      currentSession.messages = [];
      this.addMessage(
        currentSession,
        'Hello! How can I help you today?',
        false
      );
      this.saveSessions();
    }
  }

  private addMessage(
    session: ChatSession,
    content: string,
    isUser: boolean
  ): void {
    const message: Message = {
      content,
      isUser,
      timestamp: new Date(),
    };
    session.messages.push(message);
    session.lastMessageTime = new Date();

    // Update session title based on first user message
    if (isUser && session.title === 'New Chat') {
      session.title =
        content.length > 30 ? content.substring(0, 30) + '...' : content;
    }
  }

  private scrollToBottom(): void {
    try {
      this.chatMessages.nativeElement.scrollTop =
        this.chatMessages.nativeElement.scrollHeight;
    } catch (err) {
      console.error('Error scrolling to bottom:', err);
    }
  }

  private generateId(): string {
    return Math.random().toString(36).substring(2, 15);
  }

  private loadSessions(): void {
    const savedSessions = localStorage.getItem('chatSessions');
    if (savedSessions) {
      this.chatSessions = JSON.parse(savedSessions).map((session: any) => ({
        ...session,
        lastMessageTime: new Date(session.lastMessageTime),
        messages: session.messages.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp),
        })),
      }));
    }
  }

  private saveSessions(): void {
    localStorage.setItem('chatSessions', JSON.stringify(this.chatSessions));
  }
}
