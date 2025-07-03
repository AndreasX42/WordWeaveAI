import { Injectable, inject } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatDialog } from '@angular/material/dialog';
import { TranslationService } from './translation.service';

@Injectable({
  providedIn: 'root',
})
export class MessageService {
  private snackBar = inject(MatSnackBar);
  private dialog = inject(MatDialog);
  private translationService = inject(TranslationService);

  // Message getters that use translations
  get MSG_ERROR_UNKNOWN(): string {
    return this.translationService.translate('messages.unknownError');
  }

  // Keep the old typo version for backward compatibility
  get MSG_ERROR_UNKOWN(): string {
    return this.translationService.translate('messages.unknownError');
  }

  get MSG_ERROR_LOGIN_USERNAME_OR_PASSWORD_INCORRECT(): string {
    return this.translationService.translate(
      'messages.loginCredentialsIncorrect'
    );
  }

  get MSG_ERROR_NETWORK(): string {
    return this.translationService.translate('messages.networkError');
  }

  get MSG_ERROR_SERVER(): string {
    return this.translationService.translate('messages.serverError');
  }

  get MSG_WARNING_LOGIN_FIRST(): string {
    return this.translationService.translate('messages.loginFirst');
  }

  get MSG_WARNING_SESSION_EXPIRED(): string {
    return this.translationService.translate('messages.sessionExpired');
  }

  showSuccessMessage(message: string, duration = 3000): void {
    this.snackBar.open(
      message,
      this.translationService.translate('common.close'),
      {
        duration,
        panelClass: ['success-snackbar'],
        horizontalPosition: 'center',
        verticalPosition: 'bottom',
      }
    );
  }

  showErrorMessage(message: string, duration = 5000): void {
    this.snackBar.open(
      message,
      this.translationService.translate('common.close'),
      {
        duration,
        panelClass: ['error-snackbar'],
        horizontalPosition: 'center',
        verticalPosition: 'bottom',
      }
    );
  }

  showWarningMessage(message: string, duration = 4000): void {
    this.snackBar.open(
      message,
      this.translationService.translate('common.close'),
      {
        duration,
        panelClass: ['warning-snackbar'],
        horizontalPosition: 'center',
        verticalPosition: 'bottom',
      }
    );
  }

  showInfoMessage(message: string, duration = 3000): void {
    this.snackBar.open(
      message,
      this.translationService.translate('common.close'),
      {
        duration,
        panelClass: ['info-snackbar'],
        horizontalPosition: 'center',
        verticalPosition: 'bottom',
      }
    );
  }
}
