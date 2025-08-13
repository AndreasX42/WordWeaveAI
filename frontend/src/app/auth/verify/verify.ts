import {
  Component,
  DestroyRef,
  inject,
  signal,
  OnInit,
  OnDestroy,
} from '@angular/core';
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
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ErrorManagerFactory } from '../../shared/error.manager.factory';
import { AuthService } from '../../services/auth.service';
import { MessageService } from '../../services/message.service';
import { TranslationService } from '../../services/translation.service';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { TranslatePipe } from '../../shared/pipes/translate.pipe';

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
    TranslatePipe,
  ],
  templateUrl: './verify.html',
  styleUrl: './verify.scss',
})
export class Verify implements OnInit, OnDestroy {
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private authService = inject(AuthService);
  private messageService = inject(MessageService);
  private translationService = inject(TranslationService);
  private destroyRef = inject(DestroyRef);

  isVerifying = signal(false);
  isResending = signal(false);
  verificationCodeErrorMessage = signal<string>('');
  verifyError = signal<string>('');
  email = signal<string>('');

  // Resend timer state
  canResend = signal(true);
  resendCountdown = signal(0);
  private countdownTimer: number | null = null;

  form = new FormGroup({
    verificationCode: new FormControl('', {
      validators: [Validators.required, Validators.pattern(/^\d{6}$/)],
    }),
  });

  constructor() {
    // Defer route processing to ngOnInit to avoid blocking component creation
  }

  ngOnInit() {
    // Get email from route params - moved from constructor to avoid blocking
    this.route.queryParams
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((params) => {
        this.email.set(params['email'] || '');
        if (!this.email()) {
          // If no email, redirect to register
          this.router.navigate(['/register']);
        }
      });
  }

  ngOnDestroy() {
    // Clean up timer
    if (this.countdownTimer) {
      clearTimeout(this.countdownTimer);
      this.countdownTimer = null;
    }
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
        this.messageService.showSuccessMessage(
          'auth.emailVerifiedSuccessfully'
        );
        this.router.navigate(['/login'], { replaceUrl: true });
      } else {
        this.isVerifying.set(false);
        this.verifyError.set(
          this.translationService.translate('auth.invalidVerificationCode')
        );
        this.messageService.showErrorMessage('auth.invalidVerificationCode');
      }
    } catch {
      this.isVerifying.set(false);
      this.verifyError.set(
        this.translationService.translate('auth.verificationFailed')
      );
      this.messageService.showErrorMessage('auth.verificationFailed');
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
        this.messageService.showSuccessMessage('auth.verificationCodeResent');
        this.startResendTimer();
      } else {
        this.messageService.showErrorMessage('auth.resendCodeFailed');
      }
    } catch {
      this.messageService.showErrorMessage('auth.resendCodeFailed');
    } finally {
      this.isResending.set(false);
    }
  }

  private startResendTimer(): void {
    const COUNTDOWN_SECONDS = 120;
    this.canResend.set(false);
    this.resendCountdown.set(COUNTDOWN_SECONDS);

    // Use lightweight setTimeout instead of RxJS to avoid loading heavy chunks
    const countdown = () => {
      const current = this.resendCountdown();
      if (current > 0) {
        this.resendCountdown.set(current - 1);
        this.countdownTimer = setTimeout(countdown, 1000) as number;
      } else {
        this.canResend.set(true);
        this.resendCountdown.set(0);
        this.countdownTimer = null;
      }
    };

    this.countdownTimer = setTimeout(countdown, 1000) as number;
  }

  getResendButtonText(): string {
    if (this.isResending()) {
      return this.translationService.translate('auth.resendingCode');
    }

    if (!this.canResend()) {
      const minutes = Math.floor(this.resendCountdown() / 60);
      const seconds = this.resendCountdown() % 60;
      const timeString = `${minutes}:${seconds.toString().padStart(2, '0')}`;
      return this.translationService.translate('auth.resendInTime', {
        time: timeString,
      });
    }

    return this.translationService.translate('auth.resendCode');
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
