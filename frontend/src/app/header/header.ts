import { Component, input, inject } from '@angular/core';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDividerModule } from '@angular/material/divider';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Router } from '@angular/router';
import { ThemeService } from '../services/theme.service';
import { AuthService } from '../services/auth.service';

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
  private snackBar = inject(MatSnackBar);

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

  onProfile(): void {
    this.router.navigate(['/profile']);
  }
}
