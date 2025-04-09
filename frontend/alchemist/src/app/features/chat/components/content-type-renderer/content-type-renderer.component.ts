import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import {
  ContentItem,
  ContentTypeGuards,
  TableData,
} from '../../models/chat.types';

// Define CardData locally since it's missing from the imported types
interface CardData {
  title?: string;
  subtitle?: string;
  content: string;
  image?: string;
}

@Component({
  selector: 'app-content-type-renderer',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatTableModule],
  template: `
    <ng-container [ngSwitch]="content.type">
      <!-- Text content -->
      <div *ngSwitchCase="'text'" class="text-content">
        {{ content.content }}
      </div>

      <!-- Image content -->
      <div *ngSwitchCase="'image'" class="image-content">
        <img [src]="content.content" alt="Message image" />
      </div>

      <!-- Table content -->
      <div *ngSwitchCase="'table'" class="table-content">
        <table
          mat-table
          [dataSource]="
            typeGuards.isTableContent(content.content)
              ? content.content.rows
              : []
          "
        >
          <ng-container
            *ngFor="
              let column of typeGuards.isTableContent(content.content)
                ? content.content.columns
                : [];
              let i = index
            "
          >
            <ng-container [matColumnDef]="column">
              <th mat-header-cell *matHeaderCellDef>{{ column }}</th>
              <td mat-cell *matCellDef="let row">{{ row[i] }}</td>
            </ng-container>
          </ng-container>
          <tr
            mat-header-row
            *matHeaderRowDef="
              typeGuards.isTableContent(content.content)
                ? content.content.columns
                : []
            "
          ></tr>
          <tr
            mat-row
            *matRowDef="
              let row;
              columns: typeGuards.isTableContent(content.content)
                ? content.content.columns
                : []
            "
          ></tr>
        </table>
      </div>

      <!-- Card content -->
      <ng-container *ngSwitchCase="'card'">
        <mat-card class="card-content">
          <img
            *ngIf="
              typeGuards.isCardContent(content.content) && content.content.image
            "
            mat-card-image
            [src]="content.content.image"
          />
          <mat-card-header>
            <mat-card-title
              *ngIf="
                typeGuards.isCardContent(content.content) &&
                content.content.title
              "
            >
              {{ content.content.title }}
            </mat-card-title>
            <mat-card-subtitle
              *ngIf="
                typeGuards.isCardContent(content.content) &&
                content.content.subtitle
              "
            >
              {{ content.content.subtitle }}
            </mat-card-subtitle>
          </mat-card-header>
          <mat-card-content>
            {{
              typeGuards.isCardContent(content.content)
                ? content.content.content
                : ''
            }}
          </mat-card-content>
        </mat-card>
      </ng-container>

      <!-- HTML content -->
      <div
        *ngSwitchCase="'html'"
        class="html-content"
        [innerHTML]="content.content"
      ></div>
    </ng-container>
  `,
  styles: [
    `
      :host {
        display: block;
        width: 100%;
      }

      .text-content {
        font-size: 14px;
        line-height: 1.5;
        word-wrap: break-word;
      }

      .image-content {
        max-width: 100%;
        overflow: hidden;
        border-radius: 4px;

        img {
          max-width: 100%;
          height: auto;
          display: block;
        }
      }

      .table-content {
        width: 100%;
        overflow-x: auto;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 4px;

        table {
          width: 100%;
        }

        th {
          font-weight: 500;
          color: var(--text-color);
          opacity: 0.9;
        }

        td {
          color: var(--text-color);
        }
      }

      .card-content {
        width: 100%;
        background: rgba(255, 255, 255, 0.05) !important;
        border: var(--glass-border);

        img {
          max-height: 200px;
          object-fit: cover;
        }

        mat-card-title {
          color: var(--text-color);
          font-size: 16px;
        }

        mat-card-subtitle {
          color: var(--secondary-text-color);
        }

        mat-card-content {
          color: var(--text-color);
          font-size: 14px;
          line-height: 1.5;
        }
      }

      .html-content {
        width: 100%;
        overflow-x: auto;
      }

      /* Deep styling for HTML content */
      ::ng-deep .html-content {
        color: var(--text-color);
      }

      ::ng-deep .html-content a {
        color: var(--primary-color);
      }

      ::ng-deep .html-content pre,
      ::ng-deep .html-content code {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 4px;
        padding: 8px;
      }
    `,
  ],
})
export class ContentTypeRendererComponent {
  @Input() content!: ContentItem;

  typeGuards: ContentTypeGuards = {
    isCardContent: (content: any): content is CardData => {
      return content && typeof content === 'object' && 'content' in content;
    },
    isTableContent: (content: any): content is TableData => {
      return (
        content &&
        typeof content === 'object' &&
        'columns' in content &&
        'rows' in content
      );
    },
  };
}
