import { bootstrapApplication } from '@angular/platform-browser';
import { ClientSideRowModelModule, ModuleRegistry } from 'ag-grid-community';
import { AppComponent } from './app/app.component';
import { appConfig } from './app/app.config';

// Register AG Grid Modules globally
ModuleRegistry.registerModules([ClientSideRowModelModule]);

bootstrapApplication(AppComponent, appConfig).catch((err) =>
  console.error(err)
);
