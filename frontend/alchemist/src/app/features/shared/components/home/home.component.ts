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
      <mat-card>
        <mat-card-header>
          <mat-card-title>Welcome to Alchemist</mat-card-title>
          <mat-card-subtitle>AI-Powered Document Analysis</mat-card-subtitle>
        </mat-card-header>
        <mat-card-content>
          <p>
            Alchemist helps you analyze and chat with your documents using
            advanced AI technology. Upload documents and start asking questions
            about them right away.
          </p>
        </mat-card-content>
        <mat-card-actions>
          <button mat-raised-button color="primary" routerLink="/documents">
            Upload Documents
          </button>
          <button mat-raised-button color="accent" routerLink="/chat">
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
      }

      mat-card {
        max-width: 600px;
        width: 100%;
      }

      mat-card-actions {
        display: flex;
        gap: 10px;
        padding: 16px;
      }
    `,
  ],
})
export class HomeComponent {}
