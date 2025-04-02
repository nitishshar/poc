import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { ActivatedRoute } from '@angular/router';

@Component({
  selector: 'app-document-detail',
  standalone: true,
  imports: [CommonModule, MatCardModule],
  template: `
    <div class="document-detail-container">
      <mat-card>
        <mat-card-header>
          <mat-card-title>Document: {{ documentId }}</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <p>Document content will appear here.</p>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [
    `
      .document-detail-container {
        padding: 20px;
      }
    `,
  ],
})
export class DocumentDetailComponent {
  documentId: string = '';

  constructor(private route: ActivatedRoute) {
    this.route.params.subscribe((params) => {
      this.documentId = params['id'];
    });
  }
}
