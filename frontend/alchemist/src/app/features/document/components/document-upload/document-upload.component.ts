import { CommonModule } from '@angular/common';
import { Component, ElementRef, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTabsModule } from '@angular/material/tabs';
import { DocumentService } from '../../../../core/services/document.service';

enum UploadTab {
  FILE = 0,
  URL = 1,
  SERVER_PATH = 2,
}

enum FileStatus {
  READY = 'ready',
  PROCESSING = 'processing',
  UPLOADED = 'uploaded',
  FAILED = 'failed',
}

interface FileItem {
  file: File;
  status: FileStatus;
  progress: number;
  message?: string;
}

@Component({
  selector: 'app-document-upload',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatTabsModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  template: `
    <div class="upload-container">
      <div class="upload-header">
        <div class="icon-container">
          <mat-icon class="upload-icon">cloud_upload</mat-icon>
        </div>
        <div class="header-content">
          <h1>Upload Documents</h1>
          <p>
            Add documents to your knowledge base for semantic search and chat.
          </p>
        </div>
      </div>

      <mat-tab-group [(selectedIndex)]="selectedTab" animationDuration="0ms">
        <mat-tab label="File Upload">
          <div class="upload-section">
            <div
              class="file-drop-area"
              (dragover)="onDragOver($event)"
              (dragleave)="onDragLeave($event)"
              (drop)="onDrop($event)"
              [class.drag-active]="isDragging"
            >
              <div class="drop-icon-container">
                <mat-icon>cloud_upload</mat-icon>
              </div>
              <p>Drag and drop files here</p>
              <p class="file-limits">
                Limit 200MB per file • PDF, TXT, DOC, DOCX, CSV
              </p>
              <input
                type="file"
                #fileInput
                style="display: none"
                (change)="onFileSelected($event)"
                accept=".pdf,.txt,.doc,.docx,.csv"
                multiple
              />
              <button
                mat-raised-button
                color="primary"
                (click)="fileInput.click()"
              >
                Browse files
              </button>
            </div>

            <div *ngIf="selectedFiles.length > 0" class="selected-files">
              <div
                *ngFor="let fileItem of selectedFiles; let i = index"
                class="file-item"
              >
                <div class="file-info">
                  <mat-icon>description</mat-icon>
                  <span class="file-name">{{ fileItem.file.name }}</span>
                  <span class="file-size">{{
                    formatFileSize(fileItem.file.size)
                  }}</span>
                </div>
                <div class="file-actions">
                  <div
                    *ngIf="fileItem.status === 'processing'"
                    class="processing-indicator"
                  >
                    <mat-spinner diameter="20"></mat-spinner>
                    <span>Processing...</span>
                  </div>
                  <mat-icon
                    *ngIf="fileItem.status === 'uploaded'"
                    class="success-icon"
                    >check_circle</mat-icon
                  >
                  <mat-icon
                    *ngIf="fileItem.status === 'failed'"
                    class="error-icon"
                    >error</mat-icon
                  >
                  <button
                    *ngIf="fileItem.status === 'ready'"
                    mat-icon-button
                    (click)="removeFile(i)"
                  >
                    <mat-icon>close</mat-icon>
                  </button>
                </div>
              </div>
            </div>

            <div *ngIf="selectedFiles.length > 0" class="upload-summary">
              <div>Selected {{ selectedFiles.length }} files:</div>
              <button
                mat-raised-button
                color="primary"
                [disabled]="isUploading || allFilesProcessed()"
                (click)="uploadFiles()"
              >
                Upload Selected Files
              </button>
            </div>

            <div
              *ngIf="processingMessage"
              class="processing-message"
              [class]="messageClass"
            >
              <mat-icon *ngIf="messageClass === 'success-message'"
                >check_circle</mat-icon
              >
              <mat-icon *ngIf="messageClass === 'error-message'"
                >error</mat-icon
              >
              <span>{{ processingMessage }}</span>
            </div>
          </div>
        </mat-tab>

        <mat-tab label="URL Import">
          <div class="upload-section">
            <h2>Import from URLs</h2>
            <p>Enter URLs (one per line)</p>
            <textarea
              rows="10"
              placeholder="https://example.com/document.pdf&#10;https://example.com/another.pdf"
              [(ngModel)]="urlList"
            >
            </textarea>
            <button
              mat-raised-button
              color="primary"
              [disabled]="!urlList.trim()"
              (click)="importUrls()"
            >
              Import from URLs
            </button>
          </div>
        </mat-tab>

        <mat-tab label="Server Path">
          <div class="upload-section">
            <h2>Import from Server Path</h2>
            <p>Enter server file paths (one per line)</p>
            <textarea
              rows="10"
              placeholder="/path/to/document.pdf&#10;/path/to/another.pdf"
              [(ngModel)]="serverPaths"
            >
            </textarea>
            <button
              mat-raised-button
              color="primary"
              [disabled]="!serverPaths.trim()"
              (click)="importFromPaths()"
            >
              Import from Paths
            </button>
          </div>
        </mat-tab>
      </mat-tab-group>

      <div class="view-buttons">
        <button mat-raised-button (click)="viewDocuments()">
          View Documents
        </button>
        <button mat-raised-button (click)="viewStatus()">View Status</button>
      </div>
    </div>
  `,
  styles: [
    `
      .upload-container {
        padding: 20px;
        color: var(--text-color);
        background-color: var(--background-darker);
        border-radius: 0;
      }

      .upload-header {
        display: flex;
        align-items: center;
        margin-bottom: 20px;
      }

      .icon-container {
        margin-right: 16px;
      }

      .upload-icon {
        font-size: 36px;
        height: 36px;
        width: 36px;
        color: var(--text-color);
      }

      .header-content h1 {
        margin: 0;
        font-size: 24px;
        color: var(--text-color);
      }

      .header-content p {
        margin: 4px 0 0;
        opacity: 0.8;
        color: var(--secondary-text-color);
      }

      .upload-section {
        padding: 20px 0;
      }

      .file-drop-area {
        border: 2px dashed var(--drop-area-border);
        border-radius: 8px;
        padding: 30px;
        text-align: center;
        margin-bottom: 20px;
        transition: all 0.3s;
        cursor: pointer;
        background-color: transparent;
        color: var(--text-color);
      }

      .file-drop-area:hover,
      .drag-active {
        border-color: var(--primary-color);
        background-color: rgba(255, 255, 255, 0.03);
      }

      .drop-icon-container {
        margin-bottom: 10px;
      }

      .drop-icon-container mat-icon {
        font-size: 48px;
        height: 48px;
        width: 48px;
        opacity: 0.7;
        color: var(--text-color);
      }

      .file-limits {
        opacity: 0.6;
        font-size: 14px;
        margin: 8px 0 16px;
        color: var(--secondary-text-color);
      }

      .selected-files {
        margin: 20px 0;
      }

      .file-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px;
        border-radius: 4px;
        margin-bottom: 8px;
        background-color: rgba(255, 255, 255, 0.05);
      }

      .file-info {
        display: flex;
        align-items: center;
      }

      .file-info mat-icon {
        margin-right: 10px;
        opacity: 0.7;
        color: var(--text-color);
      }

      .file-name {
        margin-right: 12px;
        word-break: break-all;
        color: var(--text-color);
      }

      .file-size {
        opacity: 0.7;
        font-size: 12px;
        color: var(--secondary-text-color);
      }

      .file-actions {
        display: flex;
        align-items: center;
      }

      .processing-indicator {
        display: flex;
        align-items: center;
      }

      .processing-indicator span {
        margin-left: 8px;
        opacity: 0.7;
        color: var(--secondary-text-color);
      }

      .success-icon {
        color: var(--success-color);
      }

      .error-icon {
        color: var(--error-color);
      }

      .upload-summary {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: 20px 0;
        color: var(--text-color);
      }

      textarea {
        width: 100%;
        background-color: rgba(0, 0, 0, 0.2);
        border: 1px solid var(--border-color);
        border-radius: 4px;
        color: var(--text-color);
        padding: 10px;
        margin-bottom: 16px;
        font-family: monospace;
      }

      .processing-message {
        display: flex;
        align-items: center;
        padding: 10px;
        border-radius: 4px;
        margin-top: 16px;
        color: var(--text-color);
      }

      .processing-message mat-icon {
        margin-right: 8px;
      }

      .success-message {
        background-color: rgba(76, 175, 80, 0.1);
        border: 1px solid rgba(76, 175, 80, 0.3);
      }

      .error-message {
        background-color: rgba(244, 67, 54, 0.1);
        border: 1px solid rgba(244, 67, 54, 0.3);
      }

      .view-buttons {
        display: flex;
        justify-content: space-between;
        margin-top: 20px;
      }

      ::ng-deep .mat-mdc-tab-label-content {
        color: var(--text-color);
      }

      ::ng-deep .mat-mdc-tab-header {
        border-bottom: 1px solid var(--border-color);
      }

      ::ng-deep .mat-mdc-tab.mdc-tab--active .mat-mdc-tab-label-content {
        color: var(--primary-color);
      }

      /* Override Material button styles to match theme */
      ::ng-deep .mat-mdc-raised-button.mat-primary {
        background-color: var(--primary-color);
      }

      ::ng-deep .mat-mdc-raised-button:not(.mat-primary) {
        background-color: var(--background-lighter);
        color: var(--text-color);
      }
    `,
  ],
})
export class DocumentUploadComponent {
  @ViewChild('fileInput') fileInput!: ElementRef;

  selectedTab = UploadTab.FILE;
  isDragging = false;
  selectedFiles: FileItem[] = [];
  isUploading = false;
  processingMessage = '';
  messageClass = '';
  urlList = '';
  serverPaths = '';

  constructor(
    private documentService: DocumentService,
    private snackBar: MatSnackBar
  ) {}

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = false;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = false;

    if (event.dataTransfer?.files) {
      this.handleFiles(event.dataTransfer.files);
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files) {
      this.handleFiles(input.files);
      // Reset input to allow selecting the same file again
      this.fileInput.nativeElement.value = '';
    }
  }

  handleFiles(files: FileList): void {
    if (files.length === 0) return;

    // Check each file and add valid ones to the list
    Array.from(files).forEach((file) => {
      // Check file size (200MB limit)
      if (file.size > 200 * 1024 * 1024) {
        this.snackBar.open(
          `File ${file.name} exceeds the 200MB limit.`,
          'Dismiss',
          {
            duration: 5000,
          }
        );
        return;
      }

      // Check file type
      const extension = file.name.split('.').pop()?.toLowerCase() || '';
      const allowedExtensions = ['pdf', 'txt', 'doc', 'docx', 'csv'];
      if (!allowedExtensions.includes(extension)) {
        this.snackBar.open(
          `File ${file.name} is not an allowed file type.`,
          'Dismiss',
          {
            duration: 5000,
          }
        );
        return;
      }

      // Add file to list
      this.selectedFiles.push({
        file,
        status: FileStatus.READY,
        progress: 0,
      });
    });
  }

  removeFile(index: number): void {
    this.selectedFiles.splice(index, 1);
  }

  uploadFiles(): void {
    if (this.selectedFiles.length === 0 || this.isUploading) return;

    this.isUploading = true;
    this.processingMessage = '';

    // Process files sequentially
    this.uploadNextFile(0);
  }

  uploadNextFile(index: number): void {
    if (index >= this.selectedFiles.length) {
      this.isUploading = false;
      this.processingMessage = `Successfully processed ${
        this.selectedFiles.filter((f) => f.status === FileStatus.UPLOADED)
          .length
      } files`;
      this.messageClass = 'success-message';
      return;
    }

    const fileItem = this.selectedFiles[index];
    if (fileItem.status !== FileStatus.READY) {
      // Skip already processed files
      this.uploadNextFile(index + 1);
      return;
    }

    fileItem.status = FileStatus.PROCESSING;
    fileItem.progress = 0;
    fileItem.message = 'Processing...';

    this.documentService.uploadDocument(fileItem.file).subscribe({
      next: (document) => {
        fileItem.status = FileStatus.UPLOADED;
        fileItem.message = 'Uploaded';
        fileItem.progress = 100;
        // Process next file
        this.uploadNextFile(index + 1);
      },
      error: (error) => {
        fileItem.status = FileStatus.FAILED;
        fileItem.message = 'Failed to upload';
        console.error('Failed to upload file:', error);
        // Continue with next file despite error
        this.uploadNextFile(index + 1);
      },
    });
  }

  importUrls(): void {
    if (!this.urlList.trim()) return;

    const urls = this.urlList
      .split('\n')
      .map((url) => url.trim())
      .filter((url) => url);

    if (urls.length === 0) return;

    this.snackBar.open(
      `URL import is not yet implemented. Would import ${urls.length} URLs.`,
      'Dismiss',
      {
        duration: 5000,
      }
    );

    // Clear the input after import attempt
    this.urlList = '';
  }

  importFromPaths(): void {
    if (!this.serverPaths.trim()) return;

    const paths = this.serverPaths
      .split('\n')
      .map((path) => path.trim())
      .filter((path) => path);

    if (paths.length === 0) return;

    this.snackBar.open(
      `Server path import is not yet implemented. Would import ${paths.length} paths.`,
      'Dismiss',
      {
        duration: 5000,
      }
    );

    // Clear the input after import attempt
    this.serverPaths = '';
  }

  viewDocuments(): void {
    // Navigate to documents list view
    console.log('Navigate to documents list view');
  }

  viewStatus(): void {
    // Navigate to document status view
    console.log('Navigate to document status view');
  }

  formatFileSize(bytes: number): string {
    if (bytes < 1024) {
      return `${bytes} B`;
    } else if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    } else {
      return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    }
  }

  allFilesProcessed(): boolean {
    return this.selectedFiles.every(
      (file) =>
        file.status === FileStatus.UPLOADED || file.status === FileStatus.FAILED
    );
  }
}
