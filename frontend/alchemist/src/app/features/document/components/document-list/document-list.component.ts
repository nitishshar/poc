import { CommonModule } from '@angular/common';
import {
  Component,
  CUSTOM_ELEMENTS_SCHEMA,
  NO_ERRORS_SCHEMA,
  OnInit,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Router, RouterLink } from '@angular/router';
import { AgGridModule } from 'ag-grid-angular';
import {
  ClientSideRowModelModule,
  ColDef,
  GridApi,
  GridReadyEvent,
  ModuleRegistry,
} from 'ag-grid-community';

import {
  Document,
  DocumentStatus,
} from '../../../../core/models/document.model';
import { DocumentService } from '../../../../core/services/document.service';
import {
  ConfirmationDialogComponent,
  ConfirmationDialogData,
} from '../../../shared/components/confirmation-dialog/confirmation-dialog.component';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';

// Register AG Grid Modules
ModuleRegistry.registerModules([ClientSideRowModelModule]);

@Component({
  selector: 'app-document-list',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatListModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    LoadingSpinnerComponent,
    MatTooltipModule,
    RouterLink,
    AgGridModule,
  ],
  schemas: [CUSTOM_ELEMENTS_SCHEMA, NO_ERRORS_SCHEMA],
  template: `
    <div class="document-list-container">
      <div class="header">
        <h1>Your Documents</h1>
        <div class="actions">
          <button
            mat-raised-button
            color="primary"
            routerLink="/documents/upload"
          >
            <mat-icon>upload</mat-icon>
            Upload Document
          </button>
        </div>
      </div>

      <div class="loading-container" *ngIf="isLoading">
        <app-loading-spinner></app-loading-spinner>
      </div>

      <div class="grid-container glass-effect" *ngIf="!isLoading">
        <ag-grid-angular
          style="width: 100%; height: 100%;"
          class="ag-theme-alpine-dark"
          [rowData]="documents"
          [columnDefs]="columnDefs"
          [defaultColDef]="defaultColDef"
          [suppressRowClickSelection]="true"
          [rowSelection]="'multiple'"
          [rowModelType]="'clientSide'"
          [theme]="'legacy'"
          (gridReady)="onGridReady($event)"
        >
        </ag-grid-angular>
      </div>

      <div *ngIf="documents.length === 0 && !isLoading" class="empty-state">
        <mat-icon>folder_open</mat-icon>
        <h2>No documents found</h2>
        <p>Upload documents to get started</p>
        <button
          mat-raised-button
          color="primary"
          routerLink="/documents/upload"
        >
          Upload Document
        </button>
      </div>
    </div>
  `,
  styles: [
    `
      .document-list-container {
        padding: 20px;
        max-width: 1600px;
        margin: 0 auto;
        height: calc(100% - 40px);
        display: flex;
        flex-direction: column;
      }

      .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 24px;
      }

      .header h1 {
        font-size: 28px;
        font-weight: 400;
        margin: 0;
        color: var(--text-color);
      }

      .grid-container {
        flex: 1;
        overflow: hidden;
        border-radius: var(--border-radius);
        border: var(--glass-border);
      }

      /* AG Grid Theme Overrides */
      :host ::ng-deep .ag-theme-alpine-dark {
        --ag-background-color: transparent;
        --ag-header-background-color: rgba(30, 30, 30, 0.6);
        --ag-odd-row-background-color: rgba(0, 0, 0, 0.2);
        --ag-row-hover-color: rgba(100, 181, 246, 0.1);
        --ag-selected-row-background-color: rgba(100, 181, 246, 0.2);
        --ag-font-size: 14px;
        --ag-font-family: var(--font-family);
        --ag-border-color: var(--border-color);
        --ag-cell-horizontal-border: var(--border-color);
        --ag-header-column-separator-color: var(--border-color);
        --ag-header-foreground-color: var(--text-color);
        --ag-foreground-color: var(--text-color);
        --ag-alpine-active-color: var(--primary-color);
      }

      :host ::ng-deep .ag-theme-alpine-dark .ag-header {
        backdrop-filter: blur(var(--blur-amount));
        -webkit-backdrop-filter: blur(var(--blur-amount));
        border-bottom: var(--glass-border);
      }

      :host ::ng-deep .ag-theme-alpine-dark .ag-row {
        backdrop-filter: blur(var(--blur-amount));
        -webkit-backdrop-filter: blur(var(--blur-amount));
        transition: background-color 0.2s;
      }

      :host ::ng-deep .ag-theme-alpine-dark .ag-row:hover {
        background-color: rgba(100, 181, 246, 0.1);
      }

      :host ::ng-deep .ag-header-cell-text {
        font-weight: 500;
        color: var(--text-color);
      }

      .status-chip {
        padding: 4px 12px;
        border-radius: 16px;
        display: inline-flex;
        align-items: center;
        font-size: 12px;
        font-weight: 500;
        text-transform: uppercase;
      }

      .status-processed {
        background-color: rgba(76, 175, 80, 0.2);
        color: var(--success-color);
        border: 1px solid rgba(76, 175, 80, 0.3);
      }

      .status-processing {
        background-color: rgba(255, 152, 0, 0.2);
        color: #ff9800;
        border: 1px solid rgba(255, 152, 0, 0.3);
      }

      .status-pending {
        background-color: rgba(33, 150, 243, 0.2);
        color: #2196f3;
        border: 1px solid rgba(33, 150, 243, 0.3);
      }

      .status-failed {
        background-color: rgba(244, 67, 54, 0.2);
        color: var(--error-color);
        border: 1px solid rgba(244, 67, 54, 0.3);
      }

      .action-button {
        border: none;
        background: transparent;
        cursor: pointer;
        color: var(--text-color);
        opacity: 0.8;
        transition: all 0.2s;
        padding: 4px;
        margin: 0 4px;
      }

      .action-button:hover {
        opacity: 1;
        transform: scale(1.1);
      }

      .action-view {
        color: var(--primary-color);
      }

      .action-process {
        color: #ff9800;
      }

      .action-delete {
        color: var(--error-color);
      }

      .loading-container {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 300px;
      }

      .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 60px 0;
        text-align: center;
      }

      .empty-state mat-icon {
        font-size: 64px;
        height: 64px;
        width: 64px;
        opacity: 0.6;
        margin-bottom: 16px;
        color: var(--text-color);
      }

      .empty-state h2 {
        font-size: 24px;
        font-weight: 400;
        margin: 0 0 8px 0;
        color: var(--text-color);
      }

      .empty-state p {
        font-size: 16px;
        margin: 0 0 24px 0;
        color: var(--secondary-text-color);
      }

      @media (max-width: 600px) {
        .header {
          flex-direction: column;
          align-items: flex-start;
        }

        .actions {
          margin-top: 16px;
          width: 100%;
        }

        .actions button {
          width: 100%;
        }
      }
    `,
  ],
})
export class DocumentListComponent implements OnInit {
  documents: Document[] = [];
  isLoading = true;
  DocumentStatus = DocumentStatus;
  private gridApi!: GridApi;

  // Grid column definitions
  columnDefs: ColDef[] = [
    {
      field: 'filename',
      headerName: 'Name',
      minWidth: 250,
      flex: 2,
      cellRenderer: (params: any) => {
        const fileType = params.data.file_type || '';
        const icon = this.getFileIcon(fileType);
        return `
          <div style="display: flex; align-items: center;">
            <div style="margin-right: 10px; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center;">
              <span class="material-icons" style="color: var(--primary-color);">${icon}</span>
            </div>
            <span>${params.value}</span>
          </div>
        `;
      },
    },
    {
      field: 'file_type',
      headerName: 'Type',
      minWidth: 120,
      flex: 1,
    },
    {
      field: 'file_size',
      headerName: 'Size',
      minWidth: 100,
      flex: 1,
      valueFormatter: (params: any) => {
        return this.formatFileSize(params.value);
      },
    },
    {
      field: 'status',
      headerName: 'Status',
      minWidth: 130,
      flex: 1,
      cellRenderer: (params: any) => {
        let statusClass = '';
        if (params.value === DocumentStatus.PROCESSED) {
          statusClass = 'status-processed';
        } else if (params.value === DocumentStatus.PROCESSING) {
          statusClass = 'status-processing';
        } else if (params.value === DocumentStatus.PENDING) {
          statusClass = 'status-pending';
        } else if (params.value === DocumentStatus.FAILED) {
          statusClass = 'status-failed';
        }
        return `<div class="status-chip ${statusClass}">${params.value}</div>`;
      },
    },
    {
      field: 'created_at',
      headerName: 'Created',
      minWidth: 120,
      flex: 1,
      valueFormatter: (params: any) => {
        return this.formatDate(params.value);
      },
    },
    {
      field: 'updated_at',
      headerName: 'Updated',
      minWidth: 120,
      flex: 1,
      valueFormatter: (params: any) => {
        return this.formatDate(params.value);
      },
    },
    {
      headerName: 'Actions',
      minWidth: 150,
      flex: 1,
      pinned: 'right',
      sortable: false,
      filter: false,
      cellRenderer: (params: any) => {
        return `
          <div style="display: flex; justify-content: center;">
            <button class="action-button action-view" data-action="view" title="View Document">
              <span class="material-icons">visibility</span>
            </button>
            <button class="action-button action-process" data-action="reprocess" title="Reprocess Document">
              <span class="material-icons">refresh</span>
            </button>
            <button class="action-button action-delete" data-action="delete" title="Delete Document">
              <span class="material-icons">delete</span>
            </button>
          </div>
        `;
      },
      cellRendererParams: {
        clicked: (params: any) => {
          return (event: any) => {
            const action = event.target
              .closest('button')
              .getAttribute('data-action');
            switch (action) {
              case 'view':
                this.viewDocument(params.data.id);
                break;
              case 'reprocess':
                this.reprocessDocument(params.data);
                break;
              case 'delete':
                this.deleteDocument(params.data, event);
                break;
            }
          };
        },
      },
      onCellClicked: (params: any) => {
        const clickedElement = params.event.target as HTMLElement;
        const button = clickedElement.closest('button');
        if (button) {
          const action = button.getAttribute('data-action');
          switch (action) {
            case 'view':
              this.viewDocument(params.data.id);
              break;
            case 'reprocess':
              this.reprocessDocument(params.data);
              break;
            case 'delete':
              this.deleteDocument(params.data, params.event);
              break;
          }
        }
      },
    },
  ];

  defaultColDef: ColDef = {
    sortable: true,
    filter: true,
    resizable: true,
  };

  constructor(
    private documentService: DocumentService,
    private router: Router,
    private dialog: MatDialog
  ) {}

  ngOnInit(): void {
    this.loadDocuments();
  }

  onGridReady(params: GridReadyEvent) {
    this.gridApi = params.api;

    // Set proper sizing for grid to fit its container
    if (typeof window !== 'undefined') {
      setTimeout(() => {
        try {
          // Ensure proper column sizing by updating the state
          this.gridApi.refreshHeader();

          // Ensure the actions column is properly sized
          const actionsColIndex = this.columnDefs.findIndex(
            (col) => col.headerName === 'Actions'
          );
          if (actionsColIndex >= 0) {
            const actionCol = this.columnDefs[actionsColIndex];
            actionCol.minWidth = 150;
            actionCol.width = 150;
            actionCol.flex = 0;

            // Force a redraw
            this.gridApi.refreshCells();
          }
        } catch (error) {
          console.warn('Error setting up grid', error);
        }
      }, 100);
    }
  }

  loadDocuments(): void {
    this.isLoading = true;
    this.documentService.getAllDocuments().subscribe({
      next: (docs) => {
        this.documents = docs;
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading documents:', error);
        this.isLoading = false;
        this.createSampleDocuments();
      },
    });
  }

  createSampleDocuments(): void {
    this.documents = [
      {
        id: '1',
        filename: 'annual-report-2023.pdf',
        file_size: 1456789,
        file_type: 'pdf',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        status: DocumentStatus.PROCESSED,
        metadata: {
          page_count: 42,
          title: 'Annual Report 2023',
        },
      },
      {
        id: '2',
        filename: 'project-proposal.docx',
        file_size: 789456,
        file_type: 'docx',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        status: DocumentStatus.PROCESSING,
        metadata: {
          page_count: 15,
          title: 'Project Proposal',
        },
      },
      {
        id: '3',
        filename: 'financial-data-q3.csv',
        file_size: 345678,
        file_type: 'csv',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        status: DocumentStatus.PROCESSED,
        metadata: {
          size_bytes: 345678,
        },
      },
      {
        id: '4',
        filename: 'meeting-notes.txt',
        file_size: 12345,
        file_type: 'txt',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        status: DocumentStatus.PROCESSED,
        metadata: {},
      },
      {
        id: '5',
        filename: 'research-paper.pdf',
        file_size: 2345678,
        file_type: 'pdf',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        status: DocumentStatus.FAILED,
        metadata: {
          page_count: 28,
        },
      },
      {
        id: '6',
        filename: 'product-specifications.docx',
        file_size: 567890,
        file_type: 'docx',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        status: DocumentStatus.PENDING,
        metadata: {},
      },
      {
        id: '7',
        filename: '1q2022.pdf',
        file_size: 681800,
        file_type: 'pdf',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        status: DocumentStatus.PROCESSED,
        metadata: {},
      },
      {
        id: '8',
        filename: '2q2022.pdf',
        file_size: 707800,
        file_type: 'pdf',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        status: DocumentStatus.PROCESSED,
        metadata: {},
      },
      {
        id: '9',
        filename: '3q2022.pdf',
        file_size: 398100,
        file_type: 'pdf',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        status: DocumentStatus.PROCESSED,
        metadata: {},
      },
      {
        id: '10',
        filename: '4q2022.pdf',
        file_size: 441000,
        file_type: 'pdf',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        status: DocumentStatus.PROCESSED,
        metadata: {},
      },
    ];
  }

  getFileIcon(fileType: string): string {
    switch (fileType.toLowerCase()) {
      case 'pdf':
        return 'picture_as_pdf';
      case 'docx':
      case 'doc':
        return 'description';
      case 'csv':
        return 'table_chart';
      case 'txt':
        return 'text_snippet';
      default:
        return 'insert_drive_file';
    }
  }

  formatFileSize(bytes: number): string {
    if (bytes < 1024) {
      return `${bytes} B`;
    } else if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    } else {
      return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    }
  }

  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString();
  }

  viewDocument(documentId: string): void {
    if (documentId) {
      this.router.navigate(['/documents', documentId]);
    }
  }

  reprocessDocument(document: Document): void {
    console.log('Reprocessing document:', document);
    // Implement reprocessing logic
  }

  deleteDocument(document: Document, event: Event): void {
    // Prevent the click event from bubbling up
    event.stopPropagation();

    if (!document || !document.id) return;

    const dialogData: ConfirmationDialogData = {
      title: 'Delete Document',
      message: `Are you sure you want to delete "${
        document.filename || 'this document'
      }"? This action cannot be undone.`,
      confirmText: 'Delete',
      cancelText: 'Cancel',
      dangerous: true,
    };

    const dialogRef = this.dialog.open(ConfirmationDialogComponent, {
      data: dialogData,
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result && document.id) {
        this.documentService.deleteDocument(document.id).subscribe({
          next: () => {
            // Document deleted successfully
            this.loadDocuments();
          },
          error: (error) => {
            console.error('Error deleting document:', error);
          },
        });
      }
    });
  }

  getStatusColor(status: DocumentStatus | undefined): string {
    if (!status) return 'gray';

    switch (status) {
      case DocumentStatus.PROCESSED:
        return 'green';
      case DocumentStatus.PROCESSING:
        return 'orange';
      case DocumentStatus.PENDING:
        return 'blue';
      case DocumentStatus.FAILED:
        return 'red';
      default:
        return 'gray';
    }
  }
}
