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
import { Router, RouterLink } from '@angular/router';
import { ErrorManagerFactory } from '../../shared/error.manager.factory';
import { SimpleAuthService } from '../../services/simple-auth.service';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatSnackBar } from '@angular/material/snack-bar';

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
  private destroyRef = inject(DestroyRef);
  private authService = inject(SimpleAuthService);
  private snackBar = inject(MatSnackBar);

  hide = signal(true);
  isLoggingIn = signal(false);
  usernameErrorMessage = signal<string>('');
  passwordErrorMessage = signal<string>('');
  loginError = signal<string>('');

  form = new FormGroup({
    username: new FormControl('', {
      validators: [Validators.required, Validators.minLength(3)],
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
    this.loginError.set('');

    if (this.form.invalid) {
      this.updateUsernameErrorMessage();
      this.updatePasswordErrorMessage();
      return;
    }

    const username = this.form.value.username!;
    const password = this.form.value.password!;

    this.login(username, password);
  }

  private async login(username: string, password: string) {
    this.isLoggingIn.set(true);

    try {
      const success = await this.authService.login(username, password);

      if (success) {
        this.isLoggingIn.set(false);
        this.snackBar.open('Login successful! Welcome back.', 'Close', {
          duration: 3000,
          panelClass: ['success-snackbar'],
        });
        this.router.navigate(['/home'], { replaceUrl: true });
      } else {
        this.isLoggingIn.set(false);
        const errorMessage = 'Invalid credentials. Please try again.';
        this.loginError.set(errorMessage);
        this.snackBar.open(errorMessage, 'Close', {
          duration: 5000,
          panelClass: ['error-snackbar'],
        });
      }
    } catch (error) {
      this.isLoggingIn.set(false);
      const errorMessage = 'Login failed. Please try again.';
      this.loginError.set(errorMessage);
      this.snackBar.open(errorMessage, 'Close', {
        duration: 5000,
        panelClass: ['error-snackbar'],
      });
    }
  }

  onTogglePasswordVisibility(event: MouseEvent) {
    this.hide.set(!this.hide());
    event.stopPropagation();
  }

  updateUsernameErrorMessage = ErrorManagerFactory.getFormErrorManager(
    this.form.get('username')!,
    this.usernameErrorMessage.set,
    {
      required: ErrorManagerFactory.MSG_IS_REQUIRED,
      minlength: ErrorManagerFactory.MSG_AT_LEAST_3_CHARS,
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
