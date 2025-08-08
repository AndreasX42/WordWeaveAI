import { Component, DestroyRef, inject, OnInit, signal } from '@angular/core';
import { MatButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatDialog } from '@angular/material/dialog';
import { Router } from '@angular/router';
import { interval } from 'rxjs';
import { TitleCasePipe } from '@angular/common';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { AuthService } from '../../services/auth.service';
import { ThemeService } from '../../services/theme.service';
import { MessageService } from '../../services/message.service';
import { TranslationService } from '../../services/translation.service';
import { User } from '../../models/user.model';
import { UpdateAccountDialog } from './update-account-dialog';
import { TranslatePipe } from '../../shared/pipes/translate.pipe';
import { DatePipe } from '@angular/common';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [
    MatButton,
    MatIcon,
    MatCardModule,
    MatSlideToggleModule,
    TitleCasePipe,
    TranslatePipe,
    DatePipe,
  ],
  templateUrl: './profile.html',
  styleUrl: './profile.scss',
})
export class Profile implements OnInit {
  private router = inject(Router);
  private authService = inject(AuthService);
  private themeService = inject(ThemeService);
  private messageService = inject(MessageService);
  private translationService = inject(TranslationService);
  private destroyRef = inject(DestroyRef);
  private dialog = inject(MatDialog);

  selectedDarkMode = signal(false);
  sessionTimeLeft = signal<string>('Loading...');
  user = signal<User | null>(null);

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
      this.messageService.showSuccessMessage('auth.logoutSuccessful');
      this.router.navigate(['/home'], { replaceUrl: true });
    } catch (error) {
      console.error('Logout failed:', error);
      this.messageService.showErrorMessage('auth.logoutFailed');
    }
  }

  updateAccount(): void {
    const dialogRef = this.dialog.open(UpdateAccountDialog, {
      width: '90vw',
      maxWidth: '500px',
      minWidth: '260px',
      data: {
        user: this.user(),
      },
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result) {
        // Account was updated successfully, refresh user data
        this.user.set(this.authService.user());
      }
    });
  }

  async deleteAccount(): Promise<void> {
    const confirmed = confirm(
      this.translationService.translate('auth.deleteAccountConfirm')
    );

    if (confirmed) {
      try {
        await this.authService.deleteAccount();

        // If we reach here, deletion was successful
        this.messageService.showSuccessMessage(
          'auth.accountDeletedSuccessfully'
        );
        this.router.navigate(['/home'], { replaceUrl: true });
      } catch (error) {
        console.error('Account deletion error:', error);

        const errorMessage = (error as { message?: string })?.message || '';

        if (errorMessage === 'Session expired') {
          return;
        }

        // Display the specific error message from backend for other errors
        this.messageService.showErrorMessage(
          errorMessage || 'auth.accountDeletionFailed'
        );
      }
    }
  }

  private initializeSessionTimer(): void {
    const token = this.authService.getAuthToken();

    if (!token) {
      this.sessionTimeLeft.set(
        this.translationService.translate('auth.noSession')
      );
      return;
    }

    const tokenExpiration = this.getTokenExpiration(token);

    if (!tokenExpiration) {
      this.sessionTimeLeft.set(
        this.translationService.translate('auth.invalidSession')
      );
      return;
    }

    interval(1000)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        const now = Math.floor(Date.now() / 1000);
        const timeLeft = tokenExpiration - now;

        if (timeLeft > 0) {
          this.sessionTimeLeft.set(this.formatTimeLeft(timeLeft * 1000));
        } else {
          this.sessionTimeLeft.set(
            this.translationService.translate('auth.sessionExpired')
          );
        }
      });
  }

  private getTokenExpiration(token: string): number | null {
    try {
      const payload = token.split('.')[1];
      const decodedPayload = JSON.parse(atob(payload));

      // Return the exp field
      return decodedPayload.exp || null;
    } catch (error) {
      console.error('Failed to decode JWT token:', error);
      return null;
    }
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
