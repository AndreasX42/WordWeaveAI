import { Injectable, inject } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatDialog } from '@angular/material/dialog';
import { ErrorHandlerUtil } from '../shared/services/error-handler.util';
import { TranslationService } from './translation.service';

@Injectable({
  providedIn: 'root',
})
export class MessageService {
  private snackBar = inject(MatSnackBar);
  private dialog = inject(MatDialog);
  private translationService = inject(TranslationService);

  showSuccessMessage(message: string, duration = 3000): void {
    const translatedMessage = this.isI18nKey(message)
      ? this.translationService.translate(message)
      : message;
    this.snackBar.open(translatedMessage, 'Close', {
      duration,
      panelClass: ['success-snackbar'],
      horizontalPosition: 'center',
      verticalPosition: 'bottom',
    });
  }

  showErrorMessage(
    message: string,
    duration = 5000,
    params?: Record<string, string>
  ): void {
    const isKey = this.isI18nKey(message);
    const finalMessage = isKey
      ? this.translationService.translate(message, params)
      : message;
    const logKey = isKey ? message : finalMessage;

    ErrorHandlerUtil.logError(new Error(finalMessage), logKey);
    this.snackBar.open(finalMessage, 'Close', {
      duration,
      panelClass: ['error-snackbar'],
      horizontalPosition: 'center',
      verticalPosition: 'bottom',
    });
  }

  showWarningMessage(
    message: string,
    duration = 4000,
    params?: Record<string, string>
  ): void {
    const isKey = this.isI18nKey(message);
    const finalMessage = isKey
      ? this.translationService.translate(message, params)
      : message;
    const logKey = isKey ? message : finalMessage;

    ErrorHandlerUtil.logWarning(logKey);
    this.snackBar.open(finalMessage, 'Close', {
      duration,
      panelClass: ['warning-snackbar'],
      horizontalPosition: 'center',
      verticalPosition: 'bottom',
    });
  }

  showInfoMessage(message: string, duration = 3000): void {
    const translatedMessage = this.isI18nKey(message)
      ? this.translationService.translate(message)
      : message;
    this.snackBar.open(translatedMessage, 'Close', {
      duration,
      panelClass: ['info-snackbar'],
      horizontalPosition: 'center',
      verticalPosition: 'bottom',
    });
  }

  private isI18nKey(str: string): boolean {
    return str.includes('.') && !str.includes(' ');
  }
}
