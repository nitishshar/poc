import { Routes } from '@angular/router';

export const CHAT_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/chat-page/chat-page.component').then(
        (m) => m.ChatPageComponent
      ),
  },
  {
    path: ':id',
    loadComponent: () =>
      import('./pages/chat-detail/chat-detail.component').then(
        (m) => m.ChatDetailComponent
      ),
  },
];
