import { Component, input, inject } from '@angular/core';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDividerModule } from '@angular/material/divider';
import { Router } from '@angular/router';
import { ThemeService } from '../services/theme.service';
import { AuthService } from '../services/auth.service';
import { MessageService } from '../services/message.service';

@Component({
  selector: 'app-header',
  imports: [
    MatToolbarModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    MatTooltipModule,
    MatDividerModule,
  ],
  templateUrl: './header.html',
  styleUrl: './header.scss',
})
export class Header {
  title = input<string>();
  themeService = inject(ThemeService);
  authService = inject(AuthService);
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
}
