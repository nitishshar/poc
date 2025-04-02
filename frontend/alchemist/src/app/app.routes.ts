import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    redirectTo: 'home',
    pathMatch: 'full'
  },
  {
    path: 'home',
    loadComponent: () => import('./features/shared/components/home/home.component').then(m => m.HomeComponent)
  },
  {
    path: 'chat',
    loadChildren: () => import('./features/chat/chat.routes').then(m => m.CHAT_ROUTES)
  },
  {
    path: 'documents',
    loadChildren: () => import('./features/document/document.routes').then(m => m.DOCUMENT_ROUTES)
  },
  {
    path: '**',
    redirectTo: 'home'
  }
];
