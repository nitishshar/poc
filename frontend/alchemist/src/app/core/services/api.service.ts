import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  private baseUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  /**
   * Perform a GET request
   * @param path Endpoint path
   * @param options Request options (params, headers, etc.)
   * @returns Observable of response
   */
  get<T>(
    path: string,
    options: {
      params?: HttpParams | { [param: string]: string | string[] };
    } = {}
  ): Observable<T> {
    return this.http
      .get<T>(`${this.baseUrl}${path}`, options)
      .pipe(catchError(this.handleError));
  }

  /**
   * Perform a POST request
   * @param path Endpoint path
   * @param body Request body
   * @param options Request options (params, headers, etc.)
   * @returns Observable of response
   */
  post<T>(
    path: string,
    body: any,
    options: {
      params?: HttpParams | { [param: string]: string | string[] };
    } = {}
  ): Observable<T> {
    return this.http
      .post<T>(`${this.baseUrl}${path}`, body, options)
      .pipe(catchError(this.handleError));
  }

  /**
   * Perform a PUT request
   * @param path Endpoint path
   * @param body Request body
   * @param options Request options (params, headers, etc.)
   * @returns Observable of response
   */
  put<T>(
    path: string,
    body: any,
    options: {
      params?: HttpParams | { [param: string]: string | string[] };
    } = {}
  ): Observable<T> {
    return this.http
      .put<T>(`${this.baseUrl}${path}`, body, options)
      .pipe(catchError(this.handleError));
  }

  /**
   * Perform a PATCH request
   * @param path Endpoint path
   * @param body Request body
   * @param options Request options (params, headers, etc.)
   * @returns Observable of response
   */
  patch<T>(
    path: string,
    body: any,
    options: {
      params?: HttpParams | { [param: string]: string | string[] };
    } = {}
  ): Observable<T> {
    return this.http
      .patch<T>(`${this.baseUrl}${path}`, body, options)
      .pipe(catchError(this.handleError));
  }

  /**
   * Perform a DELETE request
   * @param path Endpoint path
   * @param options Request options (params, headers, etc.)
   * @returns Observable of response
   */
  delete<T>(
    path: string,
    options: {
      params?: HttpParams | { [param: string]: string | string[] };
    } = {}
  ): Observable<T> {
    return this.http
      .delete<T>(`${this.baseUrl}${path}`, options)
      .pipe(catchError(this.handleError));
  }

  /**
   * Upload a file
   * @param path Endpoint path
   * @param file File to upload
   * @param metadata Additional metadata
   * @returns Observable of response
   */
  uploadFile<T>(
    path: string,
    file: File,
    metadata: Record<string, any> = {}
  ): Observable<T> {
    const formData = new FormData();
    formData.append('file', file);

    // Add metadata fields
    Object.entries(metadata).forEach(([key, value]) => {
      formData.append(key, value);
    });

    return this.http
      .post<T>(`${this.baseUrl}${path}`, formData)
      .pipe(catchError(this.handleError));
  }

  /**
   * Handle HTTP errors
   * @param error HTTP error
   * @returns Observable with error
   */
  private handleError(error: any): Observable<never> {
    let errorMessage = 'An error occurred';

    if (error.error instanceof ErrorEvent) {
      // Client-side error
      errorMessage = `Error: ${error.error.message}`;
    } else {
      // Server-side error
      errorMessage = `Error Code: ${error.status}\nMessage: ${error.message}`;
    }

    console.error(errorMessage);
    return throwError(() => error);
  }
}
