import { Component, inject, signal } from '@angular/core';
import {
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators,
  AbstractControl,
} from '@angular/forms';
import { MatIcon } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { Router } from '@angular/router';
import { ErrorManagerFactory } from '../../shared/error.manager.factory';
import { AuthService } from '../../services/auth.service';
import { MessageService } from '../../services/message.service';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';

function strictEmailValidator(control: AbstractControl) {
  const email = control.value;
  if (!email) {
    return null;
  }

  // More strict email pattern that requires proper domain
  const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

  if (!emailPattern.test(email)) {
    return { invalidEmail: true };
  }

  return null;
}

@Component({
  selector: 'app-forgot-password',
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
  templateUrl: './forgot-password.html',
  styleUrl: './forgot-password.scss',
})
export class ForgotPassword {
  private router = inject(Router);
  private authService = inject(AuthService);
  private messageService = inject(MessageService);

  isSubmitting = signal(false);
  emailErrorMessage = signal<string>('');
  forgotPasswordError = signal<string>('');
  isEmailSent = signal(false);

  form = new FormGroup({
    email: new FormControl('', {
      validators: [Validators.required, strictEmailValidator],
    }),
  });

  constructor() {
    // If already logged in, redirect to home
    if (this.authService.isLoggedIn()) {
      this.router.navigate(['/home'], { replaceUrl: true });
    }
  }

  onSubmit() {
    this.forgotPasswordError.set('');

    if (this.form.invalid) {
      this.updateEmailErrorMessage();
      return;
    }

    const email = this.form.value.email!;
    this.sendResetEmail(email);
  }

  private async sendResetEmail(email: string) {
    this.isSubmitting.set(true);

    try {
      const success = await this.authService.sendPasswordResetEmail(email);

      this.isSubmitting.set(false);

      if (success) {
        this.isEmailSent.set(true);
      } else {
        // This handles cases where the request succeeds but response is malformed
        const errorMessage = 'Failed to send reset email. Please try again.';
        this.forgotPasswordError.set(errorMessage);
        this.messageService.showErrorMessage(errorMessage);
      }
    } catch (error) {
      this.isSubmitting.set(false);

      // Extract specific error message from backend if available
      const errorObj = error as {
        error?: {
          message?: string;
          details?: { error?: string };
        };
      };
      const backendMessage =
        errorObj?.error?.message || errorObj?.error?.details?.error || '';
      const errorMessage =
        backendMessage || 'Failed to send reset email. Please try again.';

      this.forgotPasswordError.set(errorMessage);
      this.messageService.showErrorMessage(errorMessage);
    }
  }

  onBackToLogin() {
    this.router.navigate(['/login']);
  }

  updateEmailErrorMessage = ErrorManagerFactory.getFormErrorManager(
    this.form.get('email')!,
    this.emailErrorMessage.set,
    {
      required: ErrorManagerFactory.MSG_IS_REQUIRED,
      invalidEmail: ErrorManagerFactory.MSG_VALID_EMAIL,
    }
  );
}
