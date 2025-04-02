import { Routes } from '@angular/router';

export const DOCUMENT_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/document-page/document-page.component').then(
        (m) => m.DocumentPageComponent
      ),
  },
  {
    path: 'upload',
    loadComponent: () =>
      import('./components/document-upload/document-upload.component').then(
        (m) => m.DocumentUploadComponent
      ),
  },
  {
    path: ':id',
    loadComponent: () =>
      import('./pages/document-detail/document-detail.component').then(
        (m) => m.DocumentDetailComponent
      ),
  }
  
];
