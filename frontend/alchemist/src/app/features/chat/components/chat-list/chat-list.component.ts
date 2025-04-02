import { Component, OnInit } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { Router } from '@angular/router';
import { Observable } from 'rxjs';
import { ChatSession } from '../../../../core/models/chat-session.model';
import { ChatService } from '../../../../core/services/chat.service';
import {
  ConfirmationDialogComponent,
  ConfirmationDialogData,
} from '../../../shared/components/confirmation-dialog/confirmation-dialog.component';

@Component({
  selector: 'app-chat-list',
  templateUrl: './chat-list.component.html',
  styleUrls: ['./chat-list.component.scss'],
})
export class ChatListComponent implements OnInit {
  chatSessions$: Observable<ChatSession[]>;
  isLoading = true;

  constructor(
    private chatService: ChatService,
    private router: Router,
    private dialog: MatDialog
  ) {
    this.chatSessions$ = this.chatService.getChatSessionsSubject();
  }

  ngOnInit(): void {
    this.loadChatSessions();
  }

  loadChatSessions(): void {
    this.isLoading = true;
    this.chatService.getAllSessions().subscribe({
      next: () => {
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading chat sessions:', error);
        this.isLoading = false;
      },
    });
  }

  openSession(sessionId: string): void {
    if (sessionId) {
      this.router.navigate(['/chat', sessionId]);
    }
  }

  createNewSession(): void {
    // Default session data
    const newSessionData = {
      name: `New Chat ${new Date().toLocaleDateString()}`,
      chat_mode: 'default',
      llm_provider: 'openai',
      llm_model: 'gpt-4',
    };

    this.chatService.createSession(newSessionData).subscribe({
      next: (session) => {
        if (session && session.id) {
          this.router.navigate(['/chat', session.id]);
        }
      },
      error: (error) => {
        console.error('Error creating new session:', error);
      },
    });
  }

  deleteSession(session: ChatSession, event: Event): void {
    // Prevent the click event from bubbling up to the parent
    event.stopPropagation();

    if (!session || !session.id) return;

    const dialogData: ConfirmationDialogData = {
      title: 'Delete Chat Session',
      message: `Are you sure you want to delete "${
        session.name || 'this session'
      }"? This action cannot be undone.`,
      confirmText: 'Delete',
      cancelText: 'Cancel',
      dangerous: true,
    };

    const dialogRef = this.dialog.open(ConfirmationDialogComponent, {
      data: dialogData,
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result && session.id) {
        this.chatService.deleteSession(session.id).subscribe({
          next: () => {
            // Session deleted successfully
          },
          error: (error) => {
            console.error('Error deleting session:', error);
          },
        });
      }
    });
  }

  formatDate(dateString: string | undefined): string {
    if (!dateString) return 'Unknown date';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString();
    } catch (e) {
      return 'Invalid date';
    }
  }
}
