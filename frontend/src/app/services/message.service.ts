import { Injectable, inject } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatDialog } from '@angular/material/dialog';

@Injectable({
  providedIn: 'root',
})
export class MessageService {
  static readonly MSG_ERROR_UNKOWN =
    'An unknown error occurred. Please try again.';
  static readonly MSG_ERROR_LOGIN_USERNAME_OR_PASSWORD_INCORRECT =
    'Invalid username or password. Please check your credentials and try again.';
  static readonly MSG_ERROR_NETWORK =
    'Network error. Please check your connection and try again.';
  static readonly MSG_ERROR_SERVER = 'Server error. Please try again later.';
  static readonly MSG_WARNING_LOGIN_FIRST =
    'Please login first to access this page.';
  static readonly MSG_WARNING_SESSION_EXPIRED =
    'Your session has expired. Please login again.';

  private snackBar = inject(MatSnackBar);
  private dialog = inject(MatDialog);

  showSuccessMessage(message: string, duration: number = 3000): void {
    this.snackBar.open(message, 'Close', {
      duration,
      panelClass: ['success-snackbar'],
      horizontalPosition: 'center',
      verticalPosition: 'bottom',
    });
  }

  showErrorMessage(message: string, duration: number = 5000): void {
    this.snackBar.open(message, 'Close', {
      duration,
      panelClass: ['error-snackbar'],
      horizontalPosition: 'center',
      verticalPosition: 'bottom',
    });
  }

  showWarningMessage(message: string, duration: number = 4000): void {
    this.snackBar.open(message, 'Close', {
      duration,
      panelClass: ['warning-snackbar'],
      horizontalPosition: 'center',
      verticalPosition: 'bottom',
    });
  }

  showInfoMessage(message: string, duration: number = 3000): void {
    this.snackBar.open(message, 'Close', {
      duration,
      panelClass: ['info-snackbar'],
      horizontalPosition: 'center',
      verticalPosition: 'bottom',
    });
  }
}
