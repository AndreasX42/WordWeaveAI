import { Component, OnInit, inject } from '@angular/core';
import { Router, ActivatedRoute } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { MessageService } from '../../services/message.service';

@Component({
  selector: 'app-callback',
  standalone: true,
  template: `
    <div
      style="display: flex; justify-content: center; align-items: center; height: 100vh;"
    >
      <div style="text-align: center;">
        <h3>Processing OAuth Login...</h3>
        <p>Please wait while we complete your authentication.</p>
        <div style="margin-top: 20px;">
          <div class="spinner"></div>
        </div>
      </div>
    </div>
  `,
  styles: [
    `
      @keyframes spin {
        0% {
          transform: rotate(0deg);
        }
        100% {
          transform: rotate(360deg);
        }
      }

      .spinner {
        width: 40px;
        height: 40px;
        border: 4px solid #f3f3f3;
        border-top: 4px solid #3498db;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin: 0 auto;
      }
    `,
  ],
})
export class AuthCallback implements OnInit {
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private authService = inject(AuthService);
  private messageService = inject(MessageService);

  async ngOnInit(): Promise<void> {
    try {
      // Extract parameters from URL
      const success = this.route.snapshot.queryParams['success'];
      const error = this.route.snapshot.queryParams['error'];
      const errorDescription =
        this.route.snapshot.queryParams['error_description'];

      // Handle error case
      if (error) {
        this.messageService.showErrorMessage(
          errorDescription || 'Google login failed. Please try again.'
        );
        this.router.navigate(['/login'], { replaceUrl: true });
        return;
      }

      // Handle success case
      if (success === 'true') {
        // The JWT is set as a cookie by the backend, try to get user info
        const loginSuccess = await this.authService.authenticateWithOAuth();

        if (loginSuccess) {
          this.messageService.showSuccessMessage('Google login successful!');
          this.router.navigate(['/profile'], { replaceUrl: true });
        } else {
          this.messageService.showErrorMessage(
            'Failed to get user information. Please try again.'
          );
          this.router.navigate(['/login'], { replaceUrl: true });
        }
      } else {
        // No valid parameters
        this.messageService.showErrorMessage(
          'Invalid login response. Please try again.'
        );
        this.router.navigate(['/login'], { replaceUrl: true });
      }
    } catch (error) {
      console.error('OAuth callback error:', error);
      this.messageService.showErrorMessage(
        'Google login failed. Please try again.'
      );
      this.router.navigate(['/login'], { replaceUrl: true });
    }
  }
}
