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
import { Router, RouterLink } from '@angular/router';
import { ErrorManagerFactory } from '../../shared/error.manager.factory';
import { AuthService } from '../../services/auth.service';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatSnackBar } from '@angular/material/snack-bar';

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
  private snackBar = inject(MatSnackBar);

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
      // Simulate API call - replace with actual service call
      const success = await this.authService.sendPasswordResetEmail(email);

      if (success) {
        this.isSubmitting.set(false);
        this.isEmailSent.set(true);
        this.snackBar.open(
          'Password reset email sent! Please check your inbox.',
          'Close',
          {
            duration: 5000,
            panelClass: ['success-snackbar'],
          }
        );
      } else {
        this.isSubmitting.set(false);
        const errorMessage = 'Failed to send reset email. Please try again.';
        this.forgotPasswordError.set(errorMessage);
        this.snackBar.open(errorMessage, 'Close', {
          duration: 5000,
          panelClass: ['error-snackbar'],
        });
      }
    } catch (error) {
      this.isSubmitting.set(false);
      const errorMessage = 'Failed to send reset email. Please try again.';
      this.forgotPasswordError.set(errorMessage);
      this.snackBar.open(errorMessage, 'Close', {
        duration: 5000,
        panelClass: ['error-snackbar'],
      });
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
