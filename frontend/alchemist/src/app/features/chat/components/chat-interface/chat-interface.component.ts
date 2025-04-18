import { CommonModule } from '@angular/common';
import {
  Component,
  ElementRef,
  OnDestroy,
  OnInit,
  ViewChild,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatListModule } from '@angular/material/list';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subject, take, takeUntil } from 'rxjs';
import { ChatExample, ChatSession, ContentItem } from '../../models/chat.types';
import { ChatService } from '../../services/chat.service';
import { ChatExamplesComponent } from '../chat-examples/chat-examples.component';
import { ContentTypeRendererComponent } from '../content-type-renderer/content-type-renderer.component';

interface TableData {
  columns: string[];
  rows: any[];
}

interface GraphData {
  type: 'line' | 'bar' | 'pie';
  data: any[];
}

interface CardData {
  title?: string;
  subtitle?: string;
  content: string;
  image?: string;
}

interface Message {
  contents: ContentItem[];
  isUser: boolean;
  timestamp: Date;
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
    MatTableModule,
    MatCardModule,
    ContentTypeRendererComponent,
    ChatExamplesComponent,
  ],
  template: `
    <div class="chat-container glass-effect">
      <div class="chat-sidebar">
        <div class="sidebar-header">
          <h3>Chat History</h3>
          <button
            mat-icon-button
            (click)="chatService.createNewChat()"
            matTooltip="New chat"
          >
            <mat-icon>add</mat-icon>
          </button>
        </div>
        <mat-nav-list class="chat-history">
          <mat-list-item
            *ngFor="let session of chatService.sessions$ | async"
            [class.active]="
              session.id === (chatService.currentSessionId$ | async)
            "
            (click)="chatService.switchSession(session.id)"
          >
            <div class="session-item">
              <div class="session-title">
                {{ chatService.generateSessionTitle(session) }}
              </div>
              <div class="session-time">
                {{ session.lastMessageTime | date : 'shortTime' }}
              </div>
            </div>
            <button
              mat-icon-button
              (click)="onDeleteSession(session.id, $event)"
              matTooltip="Delete chat"
            >
              <mat-icon>delete</mat-icon>
            </button>
          </mat-list-item>
        </mat-nav-list>
      </div>

      <div class="chat-main">
        <div class="chat-header">
          <h2>{{ getCurrentSessionTitle() }}</h2>
          <div class="chat-actions">
            <button
              mat-icon-button
              (click)="chatService.clearCurrentChat()"
              matTooltip="Clear chat"
            >
              <mat-icon>delete</mat-icon>
            </button>
          </div>
        </div>

        <div class="chat-messages" #chatMessages>
          <ng-container *ngIf="chatService.messages$ | async as messages">
            <!-- Empty chat state -->
            <div
              *ngIf="messages.length === 0 && !(chatService.loading$ | async)"
              class="empty-chat"
            >
              <div class="empty-message">
                <h3>Welcome to your chat assistant</h3>
                <p>
                  Select one of these examples or type your own message below.
                </p>
              </div>

              <!-- Only show chat examples in empty state -->
              <app-chat-examples
                [examples]="chatService.getExamples()"
                [title]="'Example questions'"
                (exampleSelected)="onExampleSelected($event)"
              ></app-chat-examples>
            </div>

            <!-- Messages display -->
            <div
              *ngFor="let message of messages"
              class="message-container"
              [class.user]="message.isUser"
            >
              <div class="message glass-effect">
                <div class="message-content">
                  <!-- Display plain text if no content items -->
                  <div class="text-content" *ngIf="!message.contentItems">
                    {{ message.content }}
                  </div>

                  <!-- Display content items if available -->
                  <ng-container
                    *ngIf="
                      message.contentItems && message.contentItems.length > 0
                    "
                  >
                    <app-content-type-renderer
                      *ngFor="let item of message.contentItems"
                      [content]="item"
                    ></app-content-type-renderer>
                  </ng-container>
                </div>
                <div class="message-timestamp">
                  {{ message.timestamp | date : 'shortTime' }}
                </div>
              </div>
            </div>
          </ng-container>

          <!-- Loading indicator -->
          <div *ngIf="chatService.loading$ | async" class="loading-container">
            <mat-progress-spinner
              diameter="24"
              mode="indeterminate"
              color="primary"
            ></mat-progress-spinner>
          </div>
        </div>

        <div class="chat-input-container">
          <!-- Only show examples in the empty chat state, not in the input area -->
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
        gap: 1px;
        background: var(--glass-background);
        border: var(--glass-border);
        border-radius: 8px;
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
        display: flex;
        flex-direction: row;
        justify-content: space-between;
        align-items: center;
        gap: 8px;
        padding: 0;
        flex: 1;
        overflow: hidden;
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

      .active {
        background: rgba(var(--primary-color-rgb), 0.1);
      }

      .chat-main {
        flex: 1;
        display: flex;
        flex-direction: column;
        overflow: hidden;
      }

      .chat-header {
        padding: 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: var(--glass-border);
      }

      .chat-messages {
        flex: 1;
        overflow-y: auto;
        padding: 16px;
        display: flex;
        flex-direction: column;
      }

      .message-container {
        display: flex;
        margin-bottom: 16px;

        &.user {
          justify-content: flex-end;

          .message {
            background: rgba(var(--primary-color-rgb), 0.05);
            border-color: rgba(var(--primary-color-rgb), 0.2);
          }
        }
      }

      .message {
        max-width: 80%;
        padding: 12px 16px;
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.05);
        border: var(--glass-border);
        box-shadow: var(--glass-shadow);
        display: flex;
        flex-direction: column;
      }

      .message-content {
        color: var(--text-color);
        font-size: 14px;
        line-height: 1.5;
        word-break: break-word;
      }

      .message-timestamp {
        font-size: 11px;
        color: var(--secondary-text-color);
        text-align: right;
        margin-top: 4px;
      }

      .chat-input-container {
        padding: 16px;
        border-top: var(--glass-border);
      }

      .chat-input {
        width: 100%;
      }

      .loading-container {
        display: flex;
        justify-content: center;
        padding: 16px;
      }

      .empty-chat {
        flex: 1;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        height: 100%;
        padding: 20px;
        max-width: 600px;
        margin: 0 auto;
      }

      .empty-message {
        color: var(--text-color);
        font-style: italic;
        text-align: center;
        padding: 20px;
        margin-bottom: 20px;
        font-size: 16px;

        h3 {
          margin-bottom: 12px;
          font-size: 24px;
          font-weight: 500;
          color: var(--primary-color);
        }

        p {
          margin: 0;
          opacity: 0.9;
        }
      }

      /* For tables */
      .text-content {
        font-size: 14px;
        line-height: 1.5;
        word-wrap: break-word;
      }

      /* For HTML content */
      .html-content {
        width: 100%;
        overflow-x: auto;
      }

      /* Deep styling for HTML content */
      ::ng-deep .html-content {
        color: var(--text-color);
      }

      ::ng-deep .html-content a {
        color: var(--primary-color);
      }

      ::ng-deep .html-content pre,
      ::ng-deep .html-content code {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 4px;
        padding: 8px;
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

      .action-buttons {
        .clear-chat-button,
        .delete-chat-button {
          color: var(--error-color);

          &:hover {
            color: var(--error-hover-color);
          }

          mat-icon {
            color: inherit;
          }
        }
      }

      .header-actions {
        .clear-chat-button,
        .delete-chat-button {
          color: var(--error-color);

          &:hover {
            color: var(--error-hover-color);
          }

          mat-icon {
            color: inherit;
          }
        }
      }
    `,
  ],
})
export class ChatInterfaceComponent implements OnInit, OnDestroy {
  @ViewChild('chatMessages') private chatMessages!: ElementRef;

  userInput = '';
  isLoading = false;
  currentSession: ChatSession | null = null;
  private destroy$ = new Subject<void>();

  constructor(public chatService: ChatService) {}

  ngOnInit(): void {
    console.log('ChatInterfaceComponent initialized');

    // Subscribe to state changes
    this.chatService
      .getState()
      .pipe(takeUntil(this.destroy$))
      .subscribe((state) => {
        console.log('Chat state updated:', state);
        this.isLoading = state.isLoading;
        this.currentSession = state.currentSession;
        console.log('Current session messages:', this.currentSession?.messages);

        // Scroll to bottom when new messages arrive
        if (this.currentSession?.messages?.length) {
          setTimeout(() => this.scrollToBottom(), 100);
        }
      });

    // Check if we need to create an initial chat
    this.chatService.sessions$.pipe(take(1)).subscribe((sessions) => {
      if (sessions.length === 0) {
        console.log('No sessions found, creating a new chat');
        this.chatService.createNewChat();

        // Add example suggestions after a short delay to ensure state is updated
        setTimeout(() => {
          console.log('Adding example suggestions');
          this.chatService.addAllExamples();
        }, 500);
      }
    });

    // Check if examples are available
    console.log('Available examples:', this.chatService.getExamples());
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  getCurrentSessionTitle(): string {
    const session = this.currentSession;
    if (!session) return 'New Chat';

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

  onDeleteSession(sessionId: string, event: Event): void {
    event.stopPropagation();
    this.chatService.deleteSession(sessionId);
  }

  sendMessage(): void {
    if (!this.userInput.trim()) return;
    this.chatService.sendMessage(this.userInput);
    this.userInput = '';
  }

  onExampleSelected(example: ChatExample): void {
    console.log('Example selected in component:', example);

    // Set the input field if it's just a text example
    if (!example.contentItems) {
      this.userInput = example.text;
    }

    // Let the service handle the example
    this.chatService.handleExampleSelection(example);
  }

  private scrollToBottom(): void {
    try {
      this.chatMessages.nativeElement.scrollTop =
        this.chatMessages.nativeElement.scrollHeight;
    } catch (err) {
      console.error('Error scrolling to bottom:', err);
    }
  }

  // Type guard for CardData
  isCardContent(content: any): content is CardData {
    return content && typeof content === 'object' && 'content' in content;
  }
}
