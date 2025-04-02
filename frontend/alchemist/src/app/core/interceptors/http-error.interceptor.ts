import {
  HttpErrorResponse,
  HttpEvent,
  HttpHandler,
  HttpInterceptor,
  HttpRequest,
} from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

@Injectable()
export class HttpErrorInterceptor implements HttpInterceptor {
  constructor() {}

  intercept(
    request: HttpRequest<unknown>,
    next: HttpHandler
  ): Observable<HttpEvent<unknown>> {
    return next.handle(request).pipe(
      catchError((error: HttpErrorResponse) => {
        let errorMessage = '';

        if (error.error instanceof ErrorEvent) {
          // Client-side error
          errorMessage = `Error: ${error.error.message}`;
        } else {
          // Server-side error
          errorMessage = this.getServerErrorMessage(error);
        }

        console.error(errorMessage);
        return throwError(() => new Error(errorMessage));
      })
    );
  }

  private getServerErrorMessage(error: HttpErrorResponse): string {
    switch (error.status) {
      case 400:
        return `Bad Request: ${this.formatErrorDetail(error)}`;
      case 401:
        return 'Unauthorized: You need to log in to access this resource';
      case 403:
        return "Forbidden: You don't have permission to access this resource";
      case 404:
        return `Not Found: The requested resource doesn't exist`;
      case 500:
        return `Internal Server Error: ${this.formatErrorDetail(error)}`;
      case 503:
        return 'Service Unavailable: The server is temporarily unavailable';
      default:
        return `Unknown Server Error: ${error.message}`;
    }
  }

  private formatErrorDetail(error: HttpErrorResponse): string {
    if (error.error && typeof error.error === 'object') {
      if (error.error.detail) {
        return error.error.detail;
      }
      if (error.error.message) {
        return error.error.message;
      }
    }
    return error.message;
  }
}
 