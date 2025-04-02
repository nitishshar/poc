import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { ActivatedRoute } from '@angular/router';

@Component({
  selector: 'app-chat-detail',
  standalone: true,
  imports: [CommonModule, MatCardModule],
  template: `
    <div class="chat-detail-container">
      <mat-card>
        <mat-card-header>
          <mat-card-title>Chat Session: {{ chatId }}</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <p>Chat messages will appear here.</p>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [
    `
      .chat-detail-container {
        padding: 20px;
      }
    `,
  ],
})
export class ChatDetailComponent {
  chatId: string = '';

  constructor(private route: ActivatedRoute) {
    this.route.params.subscribe((params) => {
      this.chatId = params['id'];
    });
  }
}
