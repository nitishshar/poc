import { CommonModule } from '@angular/common';
import {
  Component,
  CUSTOM_ELEMENTS_SCHEMA,
  OnDestroy,
  OnInit,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Router } from '@angular/router';
import { AgGridModule } from 'ag-grid-angular';
import {
  ClientSideRowModelModule,
  ColDef,
  ColumnAutoSizeModule,
  DateFilterModule,
  GridApi,
  GridReadyEvent,
  ModuleRegistry,
  NumberFilterModule,
  PaginationModule,
  RenderApiModule,
  RowApiModule,
  RowSelectionModule,
  TextFilterModule,
  ValidationModule,
} from 'ag-grid-community';

import { Subscription } from 'rxjs';
import {
  Document,
  DocumentStatus,
} from '../../../../core/models/document.model';
import { DocumentService } from '../../../../core/services/document.service';
import {
  ThemeMode,
  ThemeService,
} from '../../../../core/services/theme.service';
import {
  ConfirmationDialogComponent,
  ConfirmationDialogData,
} from '../../../shared/components/confirmation-dialog/confirmation-dialog.component';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';

// Register AG Grid Modules
ModuleRegistry.registerModules([
  ClientSideRowModelModule,
  ValidationModule,
  TextFilterModule,
  NumberFilterModule,
  DateFilterModule,
  RenderApiModule,
  RowSelectionModule,
  ColumnAutoSizeModule,
  RowApiModule,
  PaginationModule,
]);

@Component({
  selector: 'app-document-table',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    MatDialogModule,
    LoadingSpinnerComponent,
    AgGridModule,
  ],
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
  template: `
    <div class="document-table-container">
      <div class="loading-container" *ngIf="isLoading">
        <app-loading-spinner></app-loading-spinner>
      </div>


      <div class="header-actions">
        <h1 class="section-title">Your Documents</h1>
        <button
          mat-raised-button
          color="primary"
          class="upload-button"
          (click)="navigateToUpload()"
        >
          <mat-icon>cloud_upload</mat-icon> Upload Document
        </button>
      </div>

      <div class="grid-container glass-effect" *ngIf="!isLoading">
        <ag-grid-angular
          style="width: 100%; height: 100%; overflow: auto;"
          [ngClass]="gridThemeClass"
          class="ag-grid-scrollable"
          [rowData]="documents"
          [columnDefs]="columnDefs"
          [defaultColDef]="defaultColDef"
          [suppressRowClickSelection]="true"
          [rowSelection]="{ mode: 'multiRow', enableClickSelection: false }"
          [rowModelType]="'clientSide'"
          [domLayout]="'normal'"
          [theme]="'legacy'"
          (gridReady)="onGridReady($event)"
        >
        </ag-grid-angular>
      </div>

      <div *ngIf="documents.length === 0 && !isLoading" class="empty-state">
        <mat-icon>folder_open</mat-icon>
        <h2>No documents found</h2>
        <p>Upload documents to get started</p>
      </div>
    </div>
  `,
  styles: [
    `
      .document-table-container {
        height: 100%;
        min-height: 500px;
        display: flex;
        flex-direction: column;
        flex: 1;
        position: relative;
        overflow: hidden;
      }

      .tab-navigation {
        display: flex;
        border-bottom: 2px solid var(--border-color);
        margin-bottom: 24px;
        gap: 4px;
        background: rgba(30, 30, 30, 0.4);
        border-radius: var(--border-radius) var(--border-radius) 0 0;
        padding: 0 12px;
      }

      .tab-link {
        padding: 16px 24px;
        font-size: 16px;
        font-weight: 500;
        color: var(--text-color);
        text-decoration: none;
        position: relative;
        cursor: pointer;
        opacity: 0.7;
        transition: all 0.2s ease;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.4);
      }

      .tab-link:hover {
        opacity: 1;
        background-color: rgba(255, 255, 255, 0.05);
      }

      .tab-link.active {
        opacity: 1;
        font-weight: 600;
        color: var(--primary-color);
      }

      .tab-link.active::after {
        content: '';
        position: absolute;
        bottom: -2px;
        left: 0;
        width: 100%;
        height: 3px;
        background-color: var(--primary-color);
      }

      .header-actions {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
        padding: 0 8px;
      }

      .section-title {
        font-size: 24px;
        font-weight: 500;
        color: var(--text-color);
        margin: 0;
      }

      .upload-button {
        min-width: 160px;
      }

      .grid-container {
        flex: 1;
        min-height: 400px;
        overflow: hidden;
        border-radius: var(--border-radius);
        border: var(--glass-border);
        display: flex;
        flex-direction: column;
      }

      /* Ensure the grid takes appropriate space */
      .ag-grid-scrollable {
        overflow: auto !important;
      }

      /* Force scrollbars to appear */
      :host ::ng-deep .ag-body-viewport {
        overflow-y: scroll !important;
        overflow-x: auto !important;
      }

      /* Enforce minimum content height to ensure scrollbar appears */
      :host ::ng-deep .ag-center-cols-container {
        min-height: 400px !important;
      }

      :host ::ng-deep .ag-root-wrapper {
        height: 100%;
        overflow: hidden;
      }

      :host ::ng-deep .ag-layout-normal {
        height: 100%;
        overflow: hidden;
      }

      /* Add scrollbar styles */
      :host ::ng-deep .ag-body-viewport::-webkit-scrollbar {
        width: 8px;
        height: 8px;
        display: block !important;
      }

      :host ::ng-deep .ag-body-viewport::-webkit-scrollbar-track {
        background: var(--background-lighter);
      }

      :host ::ng-deep .ag-body-viewport::-webkit-scrollbar-thumb {
        background: var(--primary-color);
        border-radius: 4px;
      }

      /* AG Grid Theme Overrides */
      :host ::ng-deep .ag-theme-alpine-dark,
      :host ::ng-deep .ag-theme-alpine {
        --ag-background-color: transparent;
        --ag-font-size: 14px;
        --ag-font-family: var(--font-family);
        --ag-border-color: var(--border-color);
        --ag-cell-horizontal-border: var(--border-color);
        --ag-header-column-separator-color: var(--border-color);
        --ag-foreground-color: var(--text-color);
        --ag-header-foreground-color: var(--text-color);
        --ag-alpine-active-color: var(--primary-color);
      }

      /* Specific overrides for dark theme */
      :host ::ng-deep .ag-theme-alpine-dark {
        --ag-header-background-color: rgba(30, 30, 30, 0.6);
        --ag-odd-row-background-color: rgba(0, 0, 0, 0.2);
        --ag-row-hover-color: rgba(100, 181, 246, 0.1);
        --ag-selected-row-background-color: rgba(100, 181, 246, 0.2);
      }

      /* Specific overrides for light theme */
      :host ::ng-deep .ag-theme-alpine {
        --ag-header-background-color: rgba(240, 240, 240, 0.8);
        --ag-odd-row-background-color: rgba(240, 240, 240, 0.4);
        --ag-row-hover-color: rgba(33, 150, 243, 0.1);
        --ag-selected-row-background-color: rgba(33, 150, 243, 0.2);
      }

      :host ::ng-deep .ag-theme-alpine-dark .ag-header,
      :host ::ng-deep .ag-theme-alpine .ag-header {
        backdrop-filter: blur(var(--blur-amount));
        -webkit-backdrop-filter: blur(var(--blur-amount));
        border-bottom: var(--glass-border);
      }

      :host ::ng-deep .ag-theme-alpine-dark .ag-row,
      :host ::ng-deep .ag-theme-alpine .ag-row {
        backdrop-filter: blur(var(--blur-amount));
        -webkit-backdrop-filter: blur(var(--blur-amount));
        transition: background-color 0.2s;
      }

      .status-chip {
        padding: 4px 8px;
        border-radius: 16px;
        display: inline-flex;
        align-items: center;
        font-size: 12px;
        font-weight: 500;
        text-transform: uppercase;
      }

      .status-icon {
        font-size: 16px;
        margin-right: 4px;
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
        background-color: transparent;
        cursor: pointer;
        color: var(--text-color);
        transition: all 0.2s;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        border-radius: 4px;
        padding: 0;
        min-width: 0;
      }

      .action-button:hover {
        opacity: 0.9;
        transform: translateY(-1px);
      }

      /* Grid action buttons */
      :host ::ng-deep .grid-button {
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border: none;
        border-radius: 4px;
        width: 36px;
        height: 36px;
        transition: all 0.2s ease;
        margin: 0 2px;
      }

      :host ::ng-deep .grid-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
      }

      :host ::ng-deep .view-button {
        background-color: var(--primary-color);
        color: white;
      }

      :host ::ng-deep .process-button {
        background-color: #ff9800;
        color: white;
      }

      :host ::ng-deep .delete-button {
        background-color: var(--error-color);
        color: white;
      }

      /* Material button styling in grid */
      :host ::ng-deep .mat-raised-button.mat-primary {
        background-color: var(--primary-color);
        color: white;
      }

      :host ::ng-deep .mat-raised-button.mat-accent {
        background-color: #ff9800;
        color: white;
      }

      :host ::ng-deep .mat-raised-button.mat-warn {
        background-color: var(--error-color);
        color: white;
      }

      .action-view {
        color: white;
      }

      .action-process {
        color: white;
      }

      .action-delete {
        color: white;
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
    `,
  ],
})
export class DocumentTableComponent implements OnInit, OnDestroy {
  documents: Document[] = [];
  isLoading = true;
  DocumentStatus = DocumentStatus;
  private gridApi!: GridApi;
  private themeSubscription!: Subscription;
  gridThemeClass = 'ag-theme-alpine-dark';
  currentTheme: ThemeMode = 'dark';

  // Grid column definitions
  columnDefs: ColDef[] = [
    {
      field: 'original_filename',
      headerName: 'Name',
      minWidth: 250,
      flex: 2,
      cellRenderer: (params: any) => {
        const fileType = params.data.file_type || '';
        const icon = this.getFileIcon(fileType.replace('.', ''));
        const title = params.data.metadata?.title || '';

        return `
          <div style="display: flex; align-items: center;">
            <div style="margin-right: 10px; display: flex; align-items: center;">
              <span class="material-icons" style="color: var(--primary-color); font-size: 20px;">${icon}</span>
            </div>
            <div style="display: flex; flex-direction: column;">
              <div style="font-weight: 500;">${params.value}</div>
              ${
                title
                  ? `<div style="font-size: 12px; color: var(--secondary-text-color);">${title}</div>`
                  : ''
              }
            </div>
          </div>
        `;
      },
    },
    {
      field: 'file_type',
      headerName: 'Type',
      minWidth: 80,
      flex: 0.5,
      valueFormatter: (params: any) => {
        // Remove the dot from file extension if present
        return params.value?.startsWith('.')
          ? params.value.substring(1).toUpperCase()
          : params.value;
      },
    },
    {
      field: 'file_size',
      headerName: 'Size',
      minWidth: 100,
      flex: 0.7,
      valueFormatter: (params: any) => {
        return this.formatFileSize(params.value);
      },
    },
    {
      field: 'metadata.page_count',
      headerName: 'Pages',
      minWidth: 80,
      flex: 0.5,
      valueFormatter: (params: any) => {
        return params.value || '-';
      },
    },
    {
      field: 'status',
      headerName: 'Status',
      minWidth: 120,
      flex: 0.8,
      cellRenderer: (params: any) => {
        let statusClass = '';
        let statusIcon = '';
        const status = params.value?.toLowerCase() || '';

        if (status === 'processed') {
          statusClass = 'status-processed';
          statusIcon = 'check_circle';
        } else if (status === 'processing') {
          statusClass = 'status-processing';
          statusIcon = 'hourglass_top';
        } else if (status === 'pending') {
          statusClass = 'status-pending';
          statusIcon = 'schedule';
        } else if (status === 'failed') {
          statusClass = 'status-failed';
          statusIcon = 'error_outline';
        }

        return `
          <div class="status-chip ${statusClass}">
            <span class="material-icons status-icon">${statusIcon}</span>
            <span>${status}</span>
          </div>
        `;
      },
    },
    {
      field: 'processing_progress',
      headerName: 'Progress',
      minWidth: 120,
      flex: 1,
      cellRenderer: (params: any) => {
        const progress = params.value || 0;
        const percentage = Math.round(progress * 100);

        return `
          <div style="width: 100%; display: flex; align-items: center;">
            <div style="flex: 1; height: 8px; background: rgba(200, 200, 200, 0.2); border-radius: 4px; overflow: hidden; margin-right: 8px;">
              <div style="height: 100%; width: ${percentage}%; background-color: var(--primary-color); border-radius: 4px;"></div>
            </div>
            <div style="min-width: 40px; text-align: right;">${percentage}%</div>
          </div>
        `;
      },
    },
    {
      field: 'upload_time',
      headerName: 'Upload Date',
      minWidth: 150,
      flex: 1,
      valueFormatter: (params: any) => {
        return this.formatDate(params.value);
      },
    },
    {
      headerName: 'Actions',
      minWidth: 180,
      flex: 0.8,
      pinned: 'right',
      sortable: false,
      filter: false,
      cellRenderer: (params: any) => {
        return `
          <div style="display: flex; justify-content: center; gap: 8px;">
            <button class="grid-button view-button" data-action="view" title="View Document" (click)="viewDocument(params.data.id)">
              <span class="material-icons">visibility</span>
            </button>
            <button class="grid-button process-button" data-action="reprocess" title="Reprocess Document" (click)="reprocessDocument(params.data)">
              <span class="material-icons">refresh</span>
            </button>
            <button class="grid-button delete-button" data-action="delete" title="Delete Document" (click)="deleteDocument(params.data)">
              <span class="material-icons">delete</span>
            </button>
          </div>
        `;
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
    private dialog: MatDialog,
    private themeService: ThemeService
  ) {}

  ngOnInit(): void {
    this.loadDocuments();

    // Subscribe to theme changes
    this.themeSubscription = this.themeService.theme$.subscribe((theme) => {
      this.currentTheme = theme;
      this.gridThemeClass =
        theme === 'dark' ? 'ag-theme-alpine-dark' : 'ag-theme-alpine';

      // Refresh grid if it's already initialized
      if (this.gridApi) {
        setTimeout(() => {
          this.gridApi.refreshHeader();
          this.gridApi.refreshCells();
        }, 100);
      }
    });
  }

  ngOnDestroy(): void {
    if (this.themeSubscription) {
      this.themeSubscription.unsubscribe();
    }
  }

  onGridReady(params: GridReadyEvent) {
    this.gridApi = params.api;

    // Set proper sizing for grid to fit its container
    if (typeof window !== 'undefined') {
      setTimeout(() => {
        try {
          // Debug height issues
          const gridElement = document.querySelector(
            '.ag-root-wrapper'
          ) as HTMLElement;
          if (gridElement) {
            console.log('Grid height:', gridElement.offsetHeight);
            if (gridElement.offsetHeight < 300) {
              console.warn(
                'Grid height is less than 300px - check parent containers'
              );

              // Force minimum height as a fallback
              gridElement.style.height = '500px';
              gridElement.style.minHeight = '500px';
            }
          }

          // Enable scrollbars explicitly
          const bodyViewport = document.querySelector(
            '.ag-body-viewport'
          ) as HTMLElement;
          if (bodyViewport) {
            bodyViewport.style.overflowY = 'scroll';
            bodyViewport.style.overflowX = 'auto';
          }

          // Update CSS variables based on current theme
          this.applyThemeSpecificStyles();

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

          // Set grid size manually if needed
          this.gridApi.sizeColumnsToFit();

          // Force a grid redraw to apply all changes
          setTimeout(() => {
            this.gridApi.redrawRows();
          }, 100);
        } catch (error) {
          console.warn('Error setting up grid', error);
        }
      }, 100);
    }
  }

  private applyThemeSpecificStyles(): void {
    // No need to set theme styles here since we're using CSS variables in the component styles
    // Just trigger a refresh to ensure the grid repaints with the new theme
    if (this.gridApi) {
      this.gridApi.refreshCells({ force: true });

      // Force redraw of header as well
      this.gridApi.refreshHeader();

      // Resize columns to handle any changes in the theme affecting width
      setTimeout(() => {
        this.gridApi.sizeColumnsToFit();
      }, 150);
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
    // Create 15 sample documents to ensure scrollbars appear
    this.documents = Array(15)
      .fill(0)
      .map((_, index) => {
        const size = Math.floor(Math.random() * 2000000) + 100000;
        const types = ['pdf', 'docx', 'txt', 'csv', 'xlsx', 'pptx'];
        const fileType = types[Math.floor(Math.random() * types.length)];
        const statuses = [
          DocumentStatus.PROCESSED,
          DocumentStatus.PROCESSING,
          DocumentStatus.PENDING,
          DocumentStatus.FAILED,
        ];
        const status = statuses[Math.floor(Math.random() * statuses.length)];
        const progress =
          status === DocumentStatus.PROCESSING
            ? Math.random()
            : status === DocumentStatus.PROCESSED
            ? 1
            : 0;

        return {
          id: (index + 1).toString(),
          filename: `sample-document-${index + 1}.${fileType}`,
          original_filename: `sample-document-${index + 1}.${fileType}`,
          file_size: size,
          file_type: fileType,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          upload_time: new Date().toISOString(),
          status: status,
          processing_progress: progress,
          metadata: {
            page_count: Math.floor(Math.random() * 50) + 1,
            title: `Sample Document ${index + 1}`,
          },
        };
      });
  }

  getFileIcon(fileType: string): string {
    // Remove the leading dot if present
    const type = fileType.startsWith('.') ? fileType.substring(1) : fileType;

    switch (type.toLowerCase()) {
      case 'pdf':
        return 'picture_as_pdf';
      case 'docx':
      case 'doc':
        return 'description';
      case 'csv':
        return 'table_chart';
      case 'txt':
        return 'text_snippet';
      case 'xlsx':
      case 'xls':
        return 'analytics';
      case 'pptx':
      case 'ppt':
        return 'slideshow';
      case 'jpg':
      case 'jpeg':
      case 'png':
      case 'gif':
        return 'image';
      default:
        return 'insert_drive_file';
    }
  }

  formatFileSize(bytes: number): string {
    if (!bytes && bytes !== 0) return '-';

    if (bytes < 1024) {
      return `${bytes} B`;
    } else if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    } else if (bytes < 1024 * 1024 * 1024) {
      return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    } else {
      return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
    }
  }

  formatDate(dateString: string): string {
    if (!dateString) return 'Unknown date';

    try {
      // Try parsing as a date
      const date = new Date(dateString);

      // Check if the date is valid
      if (isNaN(date.getTime())) {
        // If not a valid date, return the original string up to 19 chars
        return dateString.substring(0, 19);
      }

      // Format the date if valid
      return (
        date.toLocaleDateString() +
        ' ' +
        date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      );
    } catch (e) {
      // Return partial string if date parsing fails
      return typeof dateString === 'string'
        ? dateString.substring(0, 19)
        : 'Unknown date';
    }
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
          next: (response:any) => {
            // Document deleted successfully
            console.log('Document deleted successfully:', response);
            this.loadDocuments();
          },
          error: (error) => {
            console.error('Error deleting document:', error);
          },
        });
      }
    });
  }

  navigateToUpload(): void {
    this.router.navigate(['/documents/upload']);
  }

  navigateToStatus(): void {
    this.router.navigate(['/documents/status']);
  }
}
