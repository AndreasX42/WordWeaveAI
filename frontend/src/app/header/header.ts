import { Component, input, inject } from '@angular/core';
import { MatToolbar } from '@angular/material/toolbar';
import { MatIconButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { MatMenu, MatMenuItem, MatMenuTrigger } from '@angular/material/menu';
import { MatTooltip } from '@angular/material/tooltip';
import { MatDivider } from '@angular/material/divider';
import { Router } from '@angular/router';
import { ThemeService } from '../services/theme.service';
import { AuthService } from '../services/auth.service';
import { MessageService } from '../services/message.service';
import { TranslationService, Language } from '../services/translation.service';
import { TranslatePipe } from '../shared/pipes/translate.pipe';

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
    TranslatePipe,
  ],
  templateUrl: './header.html',
  styleUrl: './header.scss',
})
export class Header {
  title = input<string>();
  themeService = inject(ThemeService);
  authService = inject(AuthService);
  translationService = inject(TranslationService);
  private router = inject(Router);
  private messageService = inject(MessageService);

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

  changeLanguage(languageCode: string): void {
    this.translationService.changeLanguage(languageCode);
  }

  getCurrentLanguage(): Language {
    return this.translationService.getCurrentLanguage()();
  }

  getAvailableLanguages(): Language[] {
    return this.translationService.languages;
  }
}
