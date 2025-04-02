import { Injectable, Renderer2, RendererFactory2 } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

export type ThemeMode = 'light' | 'dark';

@Injectable({
  providedIn: 'root',
})
export class ThemeService {
  private renderer: Renderer2;
  private themeSubject = new BehaviorSubject<ThemeMode>(this.getSavedTheme());
  public theme$ = this.themeSubject.asObservable();

  constructor(rendererFactory: RendererFactory2) {
    this.renderer = rendererFactory.createRenderer(null, null);
    this.initTheme();
  }

  private getSavedTheme(): ThemeMode {
    const savedTheme = localStorage.getItem('theme') as ThemeMode;
    return savedTheme || this.getPreferredTheme();
  }

  private getPreferredTheme(): ThemeMode {
    return window.matchMedia &&
      window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light';
  }

  private initTheme(): void {
    const theme = this.themeSubject.value;
    this.applyTheme(theme);
  }

  private applyTheme(theme: ThemeMode): void {
    if (theme === 'dark') {
      this.renderer.addClass(document.body, 'dark-theme');
      this.renderer.removeClass(document.body, 'light-theme');
    } else {
      this.renderer.addClass(document.body, 'light-theme');
      this.renderer.removeClass(document.body, 'dark-theme');
    }
  }

  toggleTheme(): void {
    const newTheme = this.themeSubject.value === 'light' ? 'dark' : 'light';
    this.setTheme(newTheme);
  }

  setTheme(theme: ThemeMode): void {
    localStorage.setItem('theme', theme);
    this.themeSubject.next(theme);
    this.applyTheme(theme);
  }

  getCurrentTheme(): ThemeMode {
    return this.themeSubject.value;
  }
}
