import { Injectable, ErrorHandler, inject, NgZone } from '@angular/core';
import { MessageService } from '../../services/message.service';

@Injectable({
  providedIn: 'root',
})
export class GlobalErrorHandler implements ErrorHandler {
  private messageService = inject(MessageService);
  private ngZone = inject(NgZone);

  handleError(error: any): void {
    // Log error to console for debugging
    console.error('Global error caught:', error);

    // Handle different types of errors
    this.ngZone.run(() => {
      if (this.isNetworkError(error)) {
        this.messageService.showErrorMessage(
          'Network connection lost. Please check your internet connection.',
          6000
        );
      } else if (this.isAuthError(error)) {
        this.messageService.showWarningMessage(
          'Your session has expired. Please login again.',
          5000
        );
      } else if (this.isValidationError(error)) {
        this.messageService.showErrorMessage(
          'Please check your input and try again.',
          4000
        );
      } else if (this.isChunkLoadError(error)) {
        this.messageService.showErrorMessage(
          'Application update detected. Please refresh the page.',
          8000
        );
      } else {
        // Generic error handling
        const userMessage = this.getUserFriendlyMessage(error);
        this.messageService.showErrorMessage(userMessage, 5000);
      }
    });

    // Send error to monitoring service (implement when available)
    this.sendToMonitoring(error);
  }

  private isNetworkError(error: any): boolean {
    return (
      error?.message?.includes('Http failure') ||
      error?.message?.includes('NetworkError') ||
      error?.status === 0
    );
  }

  private isAuthError(error: any): boolean {
    return (
      error?.status === 401 ||
      error?.status === 403 ||
      error?.message?.includes('authentication')
    );
  }

  private isValidationError(error: any): boolean {
    return (
      error?.status === 400 ||
      error?.status === 422 ||
      error?.message?.includes('validation')
    );
  }

  private isChunkLoadError(error: any): boolean {
    return (
      error?.message?.includes('Loading chunk') ||
      error?.message?.includes('Loading CSS chunk')
    );
  }

  private getUserFriendlyMessage(error: any): string {
    // Extract meaningful error messages
    if (error?.error?.message) {
      return error.error.message;
    }

    if (error?.message) {
      // Transform technical errors to user-friendly messages
      if (error.message.includes('Cannot read property')) {
        return 'Something went wrong. Please try again.';
      }

      if (error.message.includes('timeout')) {
        return 'Request timed out. Please try again.';
      }

      return error.message;
    }

    return 'An unexpected error occurred. Please try again.';
  }

  private sendToMonitoring(error: any): void {
    // TODO: Implement monitoring service integration
    // This could send errors to services like Sentry, LogRocket, etc.

    // For now, we'll just log structured error data
    const errorData = {
      timestamp: new Date().toISOString(),
      error: {
        message: error?.message || 'Unknown error',
        stack: error?.stack,
        status: error?.status,
        url: window.location.href,
        userAgent: navigator.userAgent,
      },
    };

    console.log('Error data for monitoring:', errorData);
  }
}
