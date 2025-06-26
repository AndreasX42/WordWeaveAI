import { Injectable, signal, effect } from '@angular/core';

@Injectable({
  providedIn: 'root',
})
export class ThemeService {
  isDarkMode = signal<boolean>(false);

  constructor() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia(
      '(prefers-color-scheme: dark)'
    ).matches;

    if (savedTheme) {
      this.isDarkMode.set(savedTheme === 'dark');
    } else {
      this.isDarkMode.set(prefersDark);
    }

    // Apply theme when signal changes
    effect(() => {
      this.applyTheme(this.isDarkMode());
    });

    // Listen for system theme changes
    window
      .matchMedia('(prefers-color-scheme: dark)')
      .addEventListener('change', (e) => {
        if (!localStorage.getItem('theme')) {
          this.isDarkMode.set(e.matches);
        }
      });
  }

  toggleTheme(): void {
    this.isDarkMode.set(!this.isDarkMode());
    localStorage.setItem('theme', this.isDarkMode() ? 'dark' : 'light');
  }

  private applyTheme(isDark: boolean): void {
    const body = document.body;
    if (isDark) {
      body.classList.add('dark-theme');
      body.classList.remove('light-theme');
    } else {
      body.classList.add('light-theme');
      body.classList.remove('dark-theme');
    }
  }
}
