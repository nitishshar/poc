import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const snackBar = inject(MatSnackBar);

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      let errorMessage = 'An error occurred';

      if (error.error instanceof ErrorEvent) {
        // Client-side error
        errorMessage = `Error: ${error.error.message}`;
      } else {
        // Server-side error
        if (error.status === 0) {
          errorMessage =
            'Cannot connect to server. Please check your connection.';
        } else if (error.status === 401) {
          errorMessage = 'Unauthorized access. Please log in again.';
          // Could redirect to login page here
        } else if (error.status === 403) {
          errorMessage =
            'Access forbidden. You do not have permission to access this resource.';
        } else if (error.status === 404) {
          errorMessage = 'Resource not found.';
        } else if (error.status === 500) {
          errorMessage = 'Server error. Please try again later.';
        } else {
          errorMessage = `${error.status}: ${error.message}`;

          // Use error.error.detail if available (FastAPI format)
          if (error.error && error.error.detail) {
            if (typeof error.error.detail === 'string') {
              errorMessage = error.error.detail;
            } else if (Array.isArray(error.error.detail)) {
              errorMessage = error.error.detail
                .map((err:any) => err.msg)
                .join(', ');
            }
          }
        }
      }

      // Show error in snackbar
      snackBar.open(errorMessage, 'Close', {
        duration: 5000,
        horizontalPosition: 'center',
        verticalPosition: 'bottom',
        panelClass: ['error-snackbar'],
      });

      // Log error to console for debugging
      console.error('HTTP Error:', error);

      // Return the error for further handling
      return throwError(() => error);
    })
  );
};
