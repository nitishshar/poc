import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ChatExample } from '../../models/chat.types';

@Component({
  selector: 'app-chat-examples',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatCardModule, MatTooltipModule],
  template: `
    <div class="chat-examples-container" *ngIf="examples.length > 0">
      <h3 class="examples-heading">
        <span>{{ title }}</span>
      </h3>
      <div class="examples-wrapper">
        <button
          *ngFor="let example of examples"
          mat-stroked-button
          class="example-item"
          [matTooltip]="example.description || ''"
          (click)="onExampleClick(example)"
        >
          {{ example.text }}
        </button>
      </div>
    </div>
  `,
  styles: [
    `
      .chat-examples-container {
        width: 100%;
        padding: 16px 0;
        margin-bottom: 16px;
        text-align: center;
      }

      .examples-heading {
        font-size: 16px;
        font-weight: 500;
        color: var(--text-color);
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        justify-content: center;

        span {
          margin-right: 8px;
        }
      }

      .examples-wrapper {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        justify-content: center;
      }

      .example-item {
        background-color: rgba(var(--primary-color-rgb), 0.1);
        color: var(--text-color);
        border: 1px solid rgba(var(--primary-color-rgb), 0.3);
        border-radius: 18px;
        padding: 8px 16px;
        font-size: 14px;
        transition: all 0.2s ease;
        white-space: nowrap;
        text-overflow: ellipsis;
        max-width: 100%;
        overflow: hidden;

        &:hover {
          background-color: rgba(var(--primary-color-rgb), 0.2);
          border-color: var(--primary-color);
          transform: translateY(-2px);
        }
      }
    `,
  ],
})
export class ChatExamplesComponent {
  @Input() examples: ChatExample[] = [];
  @Input() title: string = 'Try asking';
  @Output() exampleSelected = new EventEmitter<ChatExample>();

  onExampleClick(example: ChatExample): void {
    console.log('Example clicked:', example);
    this.exampleSelected.emit(example);
  }
}
