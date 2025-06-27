import { Component, DestroyRef, inject, OnInit, signal } from '@angular/core';
import { MatButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { Router } from '@angular/router';
import { interval } from 'rxjs';
import { TitleCasePipe } from '@angular/common';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { MatSnackBar } from '@angular/material/snack-bar';

import { AuthService } from '../../services/auth.service';
import { ThemeService } from '../../services/theme.service';
import { MessageService } from '../../services/message.service';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [
    MatButton,
    MatIcon,
    MatCardModule,
    MatSlideToggleModule,
    TitleCasePipe,
  ],
  templateUrl: './profile.html',
  styleUrl: './profile.scss',
})
export class Profile implements OnInit {
  private router = inject(Router);
  private authService = inject(AuthService);
  private themeService = inject(ThemeService);
  private messageService = inject(MessageService);
  private destroyRef = inject(DestroyRef);
  private snackBar = inject(MatSnackBar);

  selectedDarkMode = signal(false);
  sessionTimeLeft = signal<string>('Loading...');
  user = signal<any>(null);

  constructor() {
    // Check if user is logged in, redirect if not
    if (!this.authService.isLoggedIn()) {
      this.router.navigate(['/login'], { replaceUrl: true });
      return;
    }

    // Load user data
    this.user.set(this.authService.user());

    // Load theme preference
    this.selectedDarkMode.set(this.isDarkModeEnabled());
  }

  ngOnInit(): void {
    this.initializeSessionTimer();
  }

  toggleTheme(): void {
    this.themeService.toggleTheme();
    this.selectedDarkMode.set(this.isDarkModeEnabled());
  }

  private isDarkModeEnabled(): boolean {
    // Check theme service or localStorage for dark mode preference
    return this.themeService.isDarkMode?.() || false;
  }

  logout(): void {
    try {
      this.authService.logout();
      this.snackBar.open('Logout successful!', 'Close', {
        duration: 3000,
        panelClass: ['success-snackbar'],
      });
      this.router.navigate(['/home'], { replaceUrl: true });
    } catch (error) {
      console.error('Logout failed:', error);
      this.snackBar.open('Logout failed!', 'Close', {
        duration: 3000,
        panelClass: ['error-snackbar'],
      });
    }
  }

  deleteAccount(): void {
    // Show confirmation dialog
    const confirmed = confirm(
      'Are you sure you want to delete your account? This action cannot be undone.'
    );

    if (confirmed) {
      // For now, just logout since we don't have actual delete API
      // TODO: Implement actual account deletion API call
      this.authService.logout();
      this.router.navigate(['/login'], { replaceUrl: true });

      // Show success message
      // this.messageService.showSuccessModal('Account deleted successfully');
    }
  }

  private initializeSessionTimer(): void {
    // Simulate session timer - replace with actual JWT token logic
    let timeLeft = 3600000; // 1 hour in milliseconds

    interval(1000)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        if (timeLeft > 0) {
          this.sessionTimeLeft.set(this.formatTimeLeft(timeLeft));
          timeLeft -= 1000;
        } else {
          this.sessionTimeLeft.set('Session expired');
          this.authService.logout();
          this.router.navigate(['/login'], { replaceUrl: true });
        }
      });
  }

  private formatTimeLeft(timeLeft: number): string {
    const hours = Math.floor((timeLeft / 1000 / 60 / 60) % 24);
    const minutes = Math.floor((timeLeft / 1000 / 60) % 60);
    const seconds = Math.floor((timeLeft / 1000) % 60);

    if (hours > 0) {
      return `${hours}h ${minutes}m ${seconds}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds}s`;
    } else {
      return `${seconds}s`;
    }
  }
}
