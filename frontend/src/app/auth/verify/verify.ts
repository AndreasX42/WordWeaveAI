import { Component, inject, signal } from '@angular/core';
import {
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatIcon } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { Router, ActivatedRoute } from '@angular/router';
import { ErrorManagerFactory } from '../../shared/error.manager.factory';
import { SimpleAuthService } from '../../services/simple-auth.service';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatSnackBar } from '@angular/material/snack-bar';

@Component({
  selector: 'app-verify',
  standalone: true,
  imports: [
    MatButtonModule,
    MatInputModule,
    MatFormFieldModule,
    MatIcon,
    ReactiveFormsModule,
    MatProgressSpinner,
    CommonModule,
    MatCardModule,
  ],
  templateUrl: './verify.html',
  styleUrl: './verify.scss',
})
export class Verify {
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private authService = inject(SimpleAuthService);
  private snackBar = inject(MatSnackBar);

  isVerifying = signal(false);
  isResending = signal(false);
  verificationCodeErrorMessage = signal<string>('');
  verifyError = signal<string>('');
  email = signal<string>('');

  form = new FormGroup({
    verificationCode: new FormControl('', {
      validators: [Validators.required, Validators.pattern(/^\d{6}$/)],
    }),
  });

  constructor() {
    // Get email from route params
    this.route.queryParams.subscribe((params) => {
      this.email.set(params['email'] || '');
      if (!this.email()) {
        // If no email, redirect to register
        this.router.navigate(['/register']);
      }
    });
  }

  onSubmit() {
    this.verifyError.set('');

    if (this.form.invalid) {
      this.updateVerificationCodeErrorMessage();
      return;
    }

    const code = this.form.value.verificationCode!;
    this.verifyCode(code);
  }

  private async verifyCode(code: string) {
    this.isVerifying.set(true);

    try {
      const success = await this.authService.verifyEmail(this.email(), code);

      if (success) {
        this.isVerifying.set(false);
        this.snackBar.open(
          'Email verified successfully! Welcome to WordWeave.',
          'Close',
          {
            duration: 3000,
            panelClass: ['success-snackbar'],
          }
        );
        this.router.navigate(['/home'], { replaceUrl: true });
      } else {
        this.isVerifying.set(false);
        const errorMessage = 'Invalid verification code. Please try again.';
        this.verifyError.set(errorMessage);
        this.snackBar.open(errorMessage, 'Close', {
          duration: 5000,
          panelClass: ['error-snackbar'],
        });
      }
    } catch (error) {
      this.isVerifying.set(false);
      const errorMessage = 'Verification failed. Please try again.';
      this.verifyError.set(errorMessage);
      this.snackBar.open(errorMessage, 'Close', {
        duration: 5000,
        panelClass: ['error-snackbar'],
      });
    }
  }

  async onResendCode() {
    this.isResending.set(true);

    try {
      const success = await this.authService.resendVerificationCode(
        this.email()
      );

      if (success) {
        this.snackBar.open('Verification code resent to your email.', 'Close', {
          duration: 3000,
          panelClass: ['success-snackbar'],
        });
      } else {
        this.snackBar.open(
          'Failed to resend code. Please try again.',
          'Close',
          {
            duration: 5000,
            panelClass: ['error-snackbar'],
          }
        );
      }
    } catch (error) {
      this.snackBar.open('Failed to resend code. Please try again.', 'Close', {
        duration: 5000,
        panelClass: ['error-snackbar'],
      });
    } finally {
      this.isResending.set(false);
    }
  }

  updateVerificationCodeErrorMessage = ErrorManagerFactory.getFormErrorManager(
    this.form.get('verificationCode')!,
    this.verificationCodeErrorMessage.set,
    {
      required: ErrorManagerFactory.MSG_IS_REQUIRED,
      pattern: 'Please enter a valid 6-digit code',
    }
  );
}
