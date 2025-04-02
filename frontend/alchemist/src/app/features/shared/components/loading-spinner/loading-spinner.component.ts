import { NgIf } from '@angular/common';
import { Component, Input } from '@angular/core';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

@Component({
  selector: 'app-loading-spinner',
  template: `
    <div class="spinner-container" [class.overlay]="overlay">
      <mat-progress-spinner
        [diameter]="diameter"
        [mode]="mode"
        [color]="color"
        [value]="value"
      >
      </mat-progress-spinner>
      <span *ngIf="message" class="spinner-message">{{ message }}</span>
    </div>
  `,
  styles: [
    `
      .spinner-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 20px;
      }

      .spinner-container.overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(255, 255, 255, 0.7);
        z-index: 9999;
      }

      .spinner-message {
        margin-top: 10px;
        font-size: 14px;
        color: rgba(0, 0, 0, 0.54);
      }
    `,
  ],
  standalone: true,
  imports: [MatProgressSpinnerModule, NgIf],
})
export class LoadingSpinnerComponent {
  @Input() diameter: number = 40;
  @Input() mode: 'determinate' | 'indeterminate' = 'indeterminate';
  @Input() color: 'primary' | 'accent' | 'warn' = 'primary';
  @Input() value: number = 100;
  @Input() overlay: boolean = false;
  @Input() message: string = '';
}
