import { CommonModule } from '@angular/common';
import { HTTP_INTERCEPTORS } from '@angular/common/http';
import { NgModule, Optional, SkipSelf } from '@angular/core';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

// Services
import { ApiService } from './services/api.service';
import { AuthService } from './services/auth.service';
import { ChatService } from './services/chat.service';
import { DocumentService } from './services/document.service';
import { ThemeService } from './services/theme.service';

// Interceptors
import { AuthInterceptor } from './interceptors/auth.interceptor';
import { ErrorInterceptor } from './interceptors/error.interceptor';

@NgModule({
  imports: [CommonModule, BrowserAnimationsModule],
  providers: [
    ApiService,
    ChatService,
    DocumentService,
    AuthService,
    ThemeService,
    { provide: HTTP_INTERCEPTORS, useClass: AuthInterceptor, multi: true },
    { provide: HTTP_INTERCEPTORS, useClass: ErrorInterceptor, multi: true },
  ],
})
export class CoreModule {
  // Ensure CoreModule is only imported once
  constructor(@Optional() @SkipSelf() parentModule: CoreModule) {
    if (parentModule) {
      throw new Error(
        'CoreModule is already loaded. Import it in the AppModule only.'
      );
    }
  }
}
