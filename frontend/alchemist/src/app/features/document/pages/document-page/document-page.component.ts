import { CommonModule } from '@angular/common';
import { Component, CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { MatTabsModule } from '@angular/material/tabs';
import { DocumentTableComponent } from '../../components/document-table/document-table.component';
import { DocumentUploadComponent } from '../../components/document-upload/document-upload.component';

@Component({
  selector: 'app-document-page',
  standalone: true,
  imports: [
    CommonModule,
    MatTabsModule,
    DocumentUploadComponent,
    DocumentTableComponent,
  ],
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
  template: `
    <div class="document-page-container">
      <mat-tab-group animationDuration="300ms" class="glass-tabs">
        <mat-tab label="Documents">
          <div class="tab-content">
            <div class="section-header">
              <h1>Your Documents</h1>
            </div>
            <app-document-table></app-document-table>
          </div>
        </mat-tab>
        <mat-tab label="Upload">
          <div class="tab-content">
            <app-document-upload></app-document-upload>
          </div>
        </mat-tab>
        <mat-tab label="Status">
          <div class="tab-content">
            <div class="coming-soon">
              <h2>Document Processing Status</h2>
              <p>Coming soon</p>
            </div>
          </div>
        </mat-tab>
      </mat-tab-group>
    </div>
  `,
  styles: [
    `
      .document-page-container {
        height: 100%;
        display: flex;
        flex-direction: column;
      }

      .section-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
      }

      .section-header h1 {
        font-size: 28px;
        font-weight: 400;
        margin: 0;
        color: var(--text-color);
      }

      .glass-tabs ::ng-deep .mat-mdc-tab-header {
        background-color: var(--glass-background);
        backdrop-filter: blur(var(--blur-amount));
        -webkit-backdrop-filter: blur(var(--blur-amount));
        border-bottom: var(--glass-border);
        padding: 0 16px;
      }

      .glass-tabs ::ng-deep .mat-mdc-tab-header-pagination {
        display: none;
      }

      .glass-tabs ::ng-deep .mat-mdc-tab {
        height: 48px;
        opacity: 0.8;
        transition: opacity 0.3s;
      }

      .glass-tabs ::ng-deep .mat-mdc-tab:hover {
        opacity: 1;
      }

      .glass-tabs ::ng-deep .mat-mdc-tab-label-content {
        color: var(--text-color);
        text-transform: uppercase;
        font-size: 14px;
        letter-spacing: 0.5px;
      }

      /* Ensure tab text is always visible in both themes */
      :host-context(.dark-theme) ::ng-deep .mdc-tab__content {
        color: rgba(255, 255, 255, 0.87) !important;
      }

      :host-context(.light-theme) ::ng-deep .mdc-tab__content {
        color: rgba(0, 0, 0, 0.87) !important;
      }

      .glass-tabs ::ng-deep .mdc-tab--active {
        opacity: 1;
      }

      .glass-tabs ::ng-deep .mdc-tab--active .mat-mdc-tab-label-content {
        color: var(--primary-color);
        font-weight: 500;
      }

      .glass-tabs ::ng-deep .mdc-tab-indicator__content--underline {
        border-color: var(--primary-color) !important;
        border-top-width: 3px;
      }

      .tab-content {
        padding: 20px;
        height: calc(100% - 48px);
        display: flex;
        flex-direction: column;
        flex: 1;
        overflow: hidden;
      }

      .coming-soon {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 300px;
        color: var(--text-color);
        opacity: 0.7;
        text-align: center;
      }

      .coming-soon h2 {
        font-weight: 400;
        margin-bottom: 8px;
      }

      @media (max-width: 600px) {
        .section-header {
          flex-direction: column;
          align-items: flex-start;
        }

        .section-header button {
          margin-top: 16px;
          width: 100%;
        }
      }

      app-document-table {
        display: flex;
        flex-direction: column;
        flex: 1;
        height: 100%;
        min-height: 400px;
        overflow: hidden;
      }
    `,
  ],
})
export class DocumentPageComponent {}
