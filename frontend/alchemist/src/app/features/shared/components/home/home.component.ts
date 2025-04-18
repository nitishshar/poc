import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatButtonModule, RouterLink],
  template: `
    <div class="home-container">
      <mat-card class="glass-card">
        <mat-card-header>
          <mat-card-title class="title">Welcome to Alchemist</mat-card-title>
          <mat-card-subtitle class="subtitle"
            >AI-Powered Document Analysis</mat-card-subtitle
          >
        </mat-card-header>
        <mat-card-content>
          <p class="description">
            Alchemist helps you analyze and chat with your documents using
            advanced AI technology. Upload documents and start asking questions
            about them right away.
          </p>
        </mat-card-content>
        <mat-card-actions>
          <button mat-flat-button color="primary" routerLink="/documents">
            Upload Documents
          </button>
          <button mat-flat-button color="accent" routerLink="/chat">
            Start Chatting
          </button>
        </mat-card-actions>
      </mat-card>
    </div>
  `,
  styles: [
    `
      .home-container {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100%;
        padding: 20px;
        background: var(--background);
      }

      .glass-card {
        max-width: 600px;
        width: 100%;
        background: var(--glass-card-background);
        border: var(--glass-border);
        backdrop-filter: blur(var(--blur-amount));
        -webkit-backdrop-filter: blur(var(--blur-amount));
      }

      .title {
        color: var(--primary-color) !important;
        font-size: 2rem !important;
        font-weight: 600 !important;
        margin-bottom: 0.5rem !important;
      }

      .subtitle {
        color: var(--text-color) !important;
        font-size: 1.25rem !important;
        opacity: 0.9;
      }

      .description {
        color: var(--text-color);
        font-size: 1.1rem;
        line-height: 1.6;
        margin: 1.5rem 0;
        opacity: 0.9;
      }

      mat-card-actions {
        display: flex;
        gap: 16px;
        padding: 16px !important;

        button {
          flex: 1;
          padding: 8px 24px;
          font-size: 1rem;
        }
      }

      @media (max-width: 600px) {
        mat-card-actions {
          flex-direction: column;
        }
      }
    `,
  ],
})
export class HomeComponent {}
