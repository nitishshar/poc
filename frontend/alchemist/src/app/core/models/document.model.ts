/**
 * Interface representing a document with full metadata
 */
export interface Document {
  id: string;
  filename: string;
  original_filename?: string;
  file_size: number;
  file_type: string;
  upload_time?: string;
  status: string;
  current_step?: string | null;
  error_message?: string | null;
  processing_progress?: number;
  metadata?: DocumentMetadata;
  embedding_status?: string;
  processing_status?: string;
  created_at?: string; // keeping for backward compatibility
  updated_at?: string; // keeping for backward compatibility
}

/**
 * Document processing status
 */
export enum DocumentStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  PROCESSED = 'processed',
  FAILED = 'failed',
}

/**
 * Interface for document metadata
 */
export interface DocumentMetadata {
  title?: string;
  description?: string;
  page_count?: number;
  author?: string;
  created_date?: string;
  modified_date?: string;
  content_type?: string;
  source_url?: string;
  tags?: string[];
  size_bytes?: number;
  hash?: string;
  [key: string]: any; // Allow for additional metadata fields
}

/**
 * Request model for uploading a document
 */
export interface DocumentUploadRequest {
  file: File;
  metadata?: DocumentMetadata;
}
