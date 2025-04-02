import { HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { Document } from '../models/document.model';
import { ApiService } from './api.service';

@Injectable({
  providedIn: 'root',
})
export class DocumentService {
  private documents = new BehaviorSubject<Document[]>([]);
  private currentDocument = new BehaviorSubject<Document | null>(null);

  constructor(private apiService: ApiService) {}

  /**
   * Get all documents
   * @returns Observable of documents
   */
  getAllDocuments(): Observable<Document[]> {
    return this.apiService
      .get<Document[]>('/documents', { params: new HttpParams() })
      .pipe(
        tap((documents) => {
          this.documents.next(documents);
        })
      );
  }

  /**
   * Get documents as BehaviorSubject
   * @returns BehaviorSubject of documents
   */
  getDocumentsSubject(): Observable<Document[]> {
    return this.documents.asObservable();
  }

  /**
   * Get current document as BehaviorSubject
   * @returns BehaviorSubject of current document
   */
  getCurrentDocumentSubject(): Observable<Document | null> {
    return this.currentDocument.asObservable();
  }

  /**
   * Get document by ID
   * @param id Document ID
   * @returns Observable of document
   */
  getDocument(id: string): Observable<Document> {
    return this.apiService.get<Document>(`/documents/${id}`).pipe(
      tap((document) => {
        this.currentDocument.next(document);
      })
    );
  }

  /**
   * Upload document
   * @param file File to upload
   * @param metadata Additional metadata
   * @returns Observable of uploaded document
   */
  uploadDocument(
    file: File,
    metadata?: Record<string, any>
  ): Observable<Document> {
    return this.apiService
      .uploadFile<Document>('/documents/upload', file, metadata)
      .pipe(
        tap((document) => {
          const currentDocs = this.documents.value;
          this.documents.next([...currentDocs, document]);
          this.currentDocument.next(document);
        })
      );
  }

  /**
   * Delete document
   * @param id Document ID
   * @returns Observable of response
   */
  deleteDocument(id: string): Observable<void> {
    return this.apiService.delete<void>(`/documents/${id}`).pipe(
      tap(() => {
        const currentDocs = this.documents.value;
        this.documents.next(currentDocs.filter((doc) => doc.id !== id));

        const currentDoc = this.currentDocument.value;
        if (currentDoc && currentDoc.id === id) {
          this.currentDocument.next(null);
        }
      })
    );
  }

  /**
   * Check processing status of a document
   * @param documentId Document ID
   * @returns Observable of document with updated status
   */
  checkDocumentStatus(documentId: string): Observable<Document> {
    return this.apiService.get<Document>(`documents/${documentId}/status`);
  }

  /**
   * Get document content
   * @param documentId Document ID
   * @returns Observable of document content
   */
  getDocumentContent(documentId: string): Observable<string> {
    return this.apiService.get<string>(`documents/${documentId}/content`);
  }

  /**
   * Search within documents
   * @param query Search query
   * @param filters Optional filters
   * @returns Observable of search results
   */
  searchDocuments(
    query: string,
    filters?: Record<string, any>
  ): Observable<Document[]> {
    const searchParams = { query, ...filters };
    return this.apiService.post<Document[]>('documents/search', searchParams);
  }
}
