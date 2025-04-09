import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ChatInterfaceComponent } from '../../components/chat-interface/chat-interface.component';

@Component({
  selector: 'app-chat-page',
  standalone: true,
  imports: [CommonModule, ChatInterfaceComponent, MatTooltipModule],
  template: `
    <div class="chat-page-container">
      <div class="section-header">
        <h1>Chat</h1>
      </div>
      <app-chat-interface></app-chat-interface>
    </div>
  `,
  styles: [
    `
      .chat-page-container {
        height: 100%;
        display: flex;
        flex-direction: column;
        padding: 24px;
      }

      .section-header {
        margin-bottom: 24px;
      }

      .section-header h1 {
        font-size: 28px;
        font-weight: 400;
        margin: 0;
        color: var(--text-color);
      }

      app-chat-interface {
        flex: 1;
        min-height: 500px;
      }
    `,
  ],
})
export class ChatPageComponent {}
