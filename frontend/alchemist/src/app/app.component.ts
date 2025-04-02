import { NgClass } from '@angular/common';
import { Component, OnInit, ViewChild } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatMenuModule } from '@angular/material/menu';
import { MatSidenav, MatSidenavModule } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { RouterLink, RouterOutlet } from '@angular/router';
import { ThemeService } from './core/services/theme.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
  standalone: true,
  imports: [
    RouterOutlet,
    RouterLink,
    MatToolbarModule,
    MatSidenavModule,
    MatIconModule,
    MatButtonModule,
    MatListModule,
    MatMenuModule,
    NgClass,
  ],
})
export class AppComponent implements OnInit {
  title = 'Alchemist';
  @ViewChild('sidenav') sidenav!: MatSidenav;
  isDarkTheme = false;

  constructor(public themeService: ThemeService) {
    // Automatically set dark theme by default
    this.themeService.setTheme('dark');
  }

  ngOnInit(): void {
    // Subscribe to theme changes
    this.themeService.theme$.subscribe((theme) => {
      this.isDarkTheme = theme === 'dark';
    });
  }

  toggleSidenav(): void {
    if (this.sidenav) {
      this.sidenav.toggle();
    } else {
      console.warn('Sidenav is not initialized');
    }
  }

  toggleTheme(): void {
    this.themeService.toggleTheme();
  }
}
