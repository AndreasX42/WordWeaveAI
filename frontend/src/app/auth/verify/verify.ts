import { Component, DestroyRef, inject, signal } from '@angular/core';
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
import { interval } from 'rxjs';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ErrorManagerFactory } from '../../shared/error.manager.factory';
import { AuthService } from '../../services/auth.service';
import { MessageService } from '../../services/message.service';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';

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
  private authService = inject(AuthService);
  private messageService = inject(MessageService);
  private destroyRef = inject(DestroyRef);

  isVerifying = signal(false);
  isResending = signal(false);
  verificationCodeErrorMessage = signal<string>('');
  verifyError = signal<string>('');
  email = signal<string>('');

  // Resend timer state
  canResend = signal(true);
  resendCountdown = signal(0);

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
        this.messageService.showSuccessMessage('Email verified successfully!');
        this.router.navigate(['/login'], { replaceUrl: true });
      } else {
        this.isVerifying.set(false);
        const errorMessage = 'Invalid verification code. Please try again.';
        this.verifyError.set(errorMessage);
        this.messageService.showErrorMessage(errorMessage);
      }
    } catch {
      this.isVerifying.set(false);
      const errorMessage = 'Verification failed. Please try again.';
      this.verifyError.set(errorMessage);
      this.messageService.showErrorMessage(errorMessage);
    }
  }

  async onResendCode() {
    if (!this.canResend()) {
      return;
    }

    this.isResending.set(true);

    try {
      const success = await this.authService.resendVerificationCode(
        this.email()
      );

      if (success) {
        this.messageService.showSuccessMessage(
          'Verification code resent to your email.'
        );
        this.startResendTimer();
      } else {
        this.messageService.showErrorMessage(
          'Failed to resend code. Please try again.'
        );
      }
    } catch {
      this.messageService.showErrorMessage(
        'Failed to resend code. Please try again.'
      );
    } finally {
      this.isResending.set(false);
    }
  }

  private startResendTimer(): void {
    const COUNTDOWN_SECONDS = 120;
    this.canResend.set(false);
    this.resendCountdown.set(COUNTDOWN_SECONDS);

    interval(1000)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        const currentCountdown = this.resendCountdown();

        if (currentCountdown > 0) {
          this.resendCountdown.set(currentCountdown - 1);
        } else {
          this.canResend.set(true);
          this.resendCountdown.set(0);
        }
      });
  }

  getResendButtonText(): string {
    if (this.isResending()) {
      return 'Sending...';
    }

    if (!this.canResend()) {
      const minutes = Math.floor(this.resendCountdown() / 60);
      const seconds = this.resendCountdown() % 60;
      return `Resend in ${minutes}:${seconds.toString().padStart(2, '0')}`;
    }

    return 'Resend Code';
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
