import { Component, inject, signal } from '@angular/core';
import {
  AbstractControl,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatIcon } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { Router, RouterLink } from '@angular/router';
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
  selector: 'app-login',
  standalone: true,
  imports: [
    MatButtonModule,
    MatInputModule,
    MatFormFieldModule,
    MatIcon,
    ReactiveFormsModule,
    RouterLink,
    MatProgressSpinner,
    CommonModule,
    MatCardModule,
  ],
  templateUrl: './login.html',
  styleUrl: './login.scss',
})
export class Login {
  private router = inject(Router);
  private authService = inject(AuthService);
  private messageService = inject(MessageService);

  hide = signal(true);
  isLoggingIn = signal(false);
  emailErrorMessage = signal<string>('');
  passwordErrorMessage = signal<string>('');

  form = new FormGroup({
    email: new FormControl('', {
      validators: [Validators.required, strictEmailValidator],
    }),
    password: new FormControl('', {
      validators: [Validators.required, Validators.minLength(8)],
    }),
  });

  constructor() {
    // If already logged in, redirect to home
    if (this.authService.isLoggedIn()) {
      this.router.navigate(['/home'], { replaceUrl: true });
    }
  }

  onSubmit() {
    if (this.form.invalid) {
      this.updateEmailErrorMessage();
      this.updatePasswordErrorMessage();
      return;
    }

    const email = this.form.value.email!;
    const password = this.form.value.password!;

    this.login(email, password);
  }

  private async login(email: string, password: string) {
    this.isLoggingIn.set(true);

    try {
      const success = await this.authService.login(email, password);
      this.isLoggingIn.set(false);

      if (success) {
        this.messageService.showSuccessMessage('Login successful!');
        this.router.navigate(['/profile'], { replaceUrl: true });
      } else {
        this.messageService.showErrorMessage(
          'Invalid credentials. Please try again.'
        );
      }
    } catch (error) {
      this.isLoggingIn.set(false);

      const errorMessage = (error as { message?: string })?.message || '';

      switch (errorMessage) {
        case 'EMAIL_NOT_VERIFIED':
          this.messageService.showWarningMessage(
            'Please verify your email address before signing in.',
            6000
          );
          this.router.navigate(['/verify'], {
            queryParams: { email: email },
            replaceUrl: true,
          });
          break;

        case 'LOGIN_FAILED':
          this.messageService.showErrorMessage(
            'Login failed. Please try again.'
          );
          break;

        default:
          // Fallback for any unexpected errors
          this.messageService.showErrorMessage(
            'An unexpected error occurred. Please try again.'
          );
          break;
      }
    }
  }

  onTogglePasswordVisibility(event: MouseEvent) {
    this.hide.set(!this.hide());
    event.stopPropagation();
  }

  onGoogleLogin() {
    this.isLoggingIn.set(true);

    try {
      // Redirect to Google OAuth flow via backend
      this.authService.googleLogin();
    } catch {
      this.isLoggingIn.set(false);
      this.messageService.showErrorMessage(
        'Failed to initiate Google login. Please try again.'
      );
    }
  }

  updateEmailErrorMessage = ErrorManagerFactory.getFormErrorManager(
    this.form.get('email')!,
    this.emailErrorMessage.set,
    {
      required: ErrorManagerFactory.MSG_IS_REQUIRED,
      invalidEmail: ErrorManagerFactory.MSG_VALID_EMAIL,
    }
  );

  updatePasswordErrorMessage = ErrorManagerFactory.getFormErrorManager(
    this.form.get('password')!,
    this.passwordErrorMessage.set,
    {
      required: ErrorManagerFactory.MSG_IS_REQUIRED,
      minlength: ErrorManagerFactory.MSG_AT_LEAST_8_CHARS,
    }
  );
}
