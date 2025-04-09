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
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ThemeService } from '../../../../core/services/theme.service';

interface Message {
  content: string;
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
    MatProgressSpinnerModule,
  ],
  template: `
    <div class="chat-container glass-effect">
      <div class="chat-header">
        <h2>Chat</h2>
        <div class="chat-actions">
          <button mat-icon-button (click)="clearChat()" matTooltip="Clear chat">
            <mat-icon>delete</mat-icon>
          </button>
        </div>
      </div>

      <div class="chat-messages" #chatMessages>
        <div
          *ngFor="let message of messages"
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
  `,
  styles: [
    `
      .chat-container {
        display: flex;
        flex-direction: column;
        height: 100%;
        min-height: 500px;
        border-radius: var(--border-radius);
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

  messages: Message[] = [];
  userInput = '';
  isLoading = false;

  constructor(@Inject(ThemeService) private themeService: ThemeService) {}

  ngOnInit(): void {
    // Add welcome message
    this.addMessage('Hello! How can I help you today?', false);
  }

  sendMessage(): void {
    if (!this.userInput.trim()) return;

    // Add user message
    this.addMessage(this.userInput, true);
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
        'This is a simulated response. Replace with actual API call.',
        false
      );
      this.isLoading = false;
      this.scrollToBottom();
    }, 1000);
  }

  clearChat(): void {
    this.messages = [];
    this.addMessage('Hello! How can I help you today?', false);
  }

  private addMessage(content: string, isUser: boolean): void {
    this.messages.push({
      content,
      isUser,
      timestamp: new Date(),
    });
  }

  private scrollToBottom(): void {
    try {
      this.chatMessages.nativeElement.scrollTop =
        this.chatMessages.nativeElement.scrollHeight;
    } catch (err) {
      console.error('Error scrolling to bottom:', err);
    }
  }
}
