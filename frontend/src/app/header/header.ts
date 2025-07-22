import { Component, input, inject, OnInit, OnDestroy } from '@angular/core';
import { MatToolbar } from '@angular/material/toolbar';
import { MatIconButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { MatMenu, MatMenuItem, MatMenuTrigger } from '@angular/material/menu';
import { MatTooltip } from '@angular/material/tooltip';
import { MatDivider } from '@angular/material/divider';
import { MatBadge } from '@angular/material/badge';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ThemeService } from '../services/theme.service';
import { AuthService } from '../services/auth.service';
import { MessageService } from '../services/message.service';
import { TranslationService, Language } from '../services/translation.service';
import {
  NotificationService,
  NotificationItem,
} from '../services/notification.service';
import { TranslatePipe } from '../shared/pipes/translate.pipe';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-header',
  imports: [
    MatToolbar,
    MatIconButton,
    MatIcon,
    MatMenu,
    MatMenuItem,
    MatMenuTrigger,
    MatTooltip,
    MatDivider,
    MatBadge,
    MatProgressSpinner,
    CommonModule,
    TranslatePipe,
  ],
  templateUrl: './header.html',
  styleUrl: './header.scss',
})
export class Header implements OnInit, OnDestroy {
  title = input<string>();
  themeService = inject(ThemeService);
  authService = inject(AuthService);
  translationService = inject(TranslationService);
  notificationService = inject(NotificationService);
  private router = inject(Router);
  private messageService = inject(MessageService);
  private subscriptions = new Subscription();

  ngOnInit(): void {
    // Subscribe to notification updates for potential sound effects or animations
    this.subscriptions.add(
      this.notificationService.notificationUpdate$.subscribe(() => {
        // Could add subtle sound effect or animation here
      })
    );
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  toggleTheme(): void {
    this.themeService.toggleTheme();
  }

  onLogoClick(): void {
    this.router.navigate(['/home']);
  }

  onLogin(): void {
    this.router.navigate(['/login']);
  }

  onRegister(): void {
    this.router.navigate(['/register']);
  }

  onLogout(): void {
    try {
      this.authService.logout();
      this.messageService.showSuccessMessage('Logout successful!');
      this.router.navigate(['/home'], { replaceUrl: true });
    } catch (error) {
      console.error('Logout failed:', error);
      this.messageService.showErrorMessage('Logout failed!');
    }
  }

  onProfile(): void {
    this.router.navigate(['/profile']);
  }

  onHealth(): void {
    this.router.navigate(['/health']);
  }

  onSearch(): void {
    this.router.navigate(['/search']);
  }

  changeLanguage(languageCode: string): void {
    this.translationService.changeLanguage(languageCode);
  }

  getCurrentLanguage(): Language {
    return this.translationService.getCurrentLanguage()();
  }

  getAvailableLanguages(): Language[] {
    return this.translationService.languages;
  }

  onNotificationClick(): void {
    // Mark all notifications as seen when dropdown is opened
    this.notificationService.markAllAsSeen();
  }

  onNotificationItemClick(notification: NotificationItem): void {
    this.notificationService.handleNotificationClick(notification);
  }

  removeNotification(event: Event, notificationId: string): void {
    event.stopPropagation();
    this.notificationService.removeNotification(notificationId);
  }

  clearAllNotifications(): void {
    this.notificationService.clearAll();
  }

  getNotificationTimeAgo(timestamp: number): string {
    const now = Date.now();
    const diff = now - timestamp;
    const minutes = Math.floor(diff / (1000 * 60));
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return `${days}d ago`;
  }
}
