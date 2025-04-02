import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { MatCardModule } from '@angular/material/card';

@Component({
  selector: 'app-chat-page',
  standalone: true,
  imports: [CommonModule, MatCardModule],
  template: `
    <div class="chat-container">
      <mat-card>
        <mat-card-header>
          <mat-card-title>Chat Sessions</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <p>Your chat sessions will appear here.</p>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [
    `
      .chat-container {
        padding: 20px;
      }
    `,
  ],
})
export class ChatPageComponent {}
