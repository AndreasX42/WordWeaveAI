import { Injectable, ErrorHandler, inject, NgZone } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { MessageService } from '../../services/message.service';
import { Configs } from '../config';

@Injectable({
  providedIn: 'root',
})
export class GlobalErrorHandler implements ErrorHandler {
  private messageService = inject(MessageService);
  private ngZone = inject(NgZone);

  handleError(error: any): void {
    // Log error to console for debugging
    console.error('Global error caught:', error);

    // Skip errors that are already handled by interceptors
    if (this.isHandledByInterceptor(error)) {
      // Only log for monitoring, don't show user message
      this.sendToMonitoring(error);
      return;
    }

    // Skip errors that are marked as handled by components
    if (this.isHandledByComponent(error)) {
      console.log(
        'Error marked as handled by component, skipping global message'
      );
      this.sendToMonitoring(error);
      return;
    }

    // Handle different types of errors
    this.ngZone.run(() => {
      if (this.isHttpError(error)) {
        this.handleHttpError(error);
      } else if (this.isChunkLoadError(error)) {
        this.messageService.showErrorMessage(
          'Application update detected. Please refresh the page.',
          8000
        );
      } else if (this.isScriptError(error)) {
        this.messageService.showErrorMessage(
          'A script error occurred. Please refresh the page.',
          5000
        );
      } else if (this.isPromiseRejection(error)) {
        this.handlePromiseRejection(error);
      } else {
        // Generic error handling
        const userMessage = this.getUserFriendlyMessage(error);
        this.messageService.showErrorMessage(userMessage, 5000);
      }
    });

    this.sendToMonitoring(error);
  }

  private isHttpError(error: any): boolean {
    return (
      error instanceof HttpErrorResponse ||
      (error?.status !== undefined && typeof error.status === 'number')
    );
  }

  private handleHttpError(error: HttpErrorResponse | any): void {
    const status = error.status || 0;

    // Check if this is a validation error from update account endpoint
    if (this.isUpdateAccountValidationError(error)) {
      console.log('Global handler: Skipping update account validation error');
      return;
    }

    switch (status) {
      case 0:
        // Network error
        this.messageService.showErrorMessage(
          'Network connection lost. Please check your internet connection.',
          6000
        );
        break;

      case 400:
        // Bad request
        const badRequestMessage =
          this.extractErrorMessage(error) ||
          'Please check your input and try again.';
        this.messageService.showErrorMessage(badRequestMessage, 4000);
        break;

      case 401:
        // Unauthorized - this should be handled by interceptor
        // Don't show message here as interceptor already handles it
        console.log(
          '401 error caught by global handler - should be handled by interceptor'
        );
        break;

      case 403:
        // Forbidden
        this.messageService.showErrorMessage(
          'You do not have permission to perform this action.',
          5000
        );
        break;

      case 404:
        // Not found
        this.messageService.showErrorMessage(
          'The requested resource was not found.',
          4000
        );
        break;

      case 409:
        // Conflict - could be validation error, let component handle it
        console.log(
          'Global handler: 409 Conflict - letting component handle it'
        );
        break;

      case 422:
        // Validation error
        const validationMessage =
          this.extractErrorMessage(error) ||
          'Please check your input and try again.';
        this.messageService.showErrorMessage(validationMessage, 4000);
        break;

      case 429:
        // Too many requests
        this.messageService.showWarningMessage(
          'Too many requests. Please wait a moment and try again.',
          6000
        );
        break;

      case 500:
        // Internal server error
        this.messageService.showErrorMessage(
          'Server error. Please try again later.',
          5000
        );
        break;

      case 502:
      case 503:
      case 504:
        // Service unavailable
        this.messageService.showErrorMessage(
          'Service temporarily unavailable. Please try again later.',
          6000
        );
        break;

      default:
        // Generic HTTP error
        const genericMessage =
          this.extractErrorMessage(error) ||
          `Request failed (${status}). Please try again.`;
        this.messageService.showErrorMessage(genericMessage, 5000);
    }
  }

  private isChunkLoadError(error: any): boolean {
    return (
      error?.message?.includes('Loading chunk') ||
      error?.message?.includes('Loading CSS chunk') ||
      error?.message?.includes('ChunkLoadError')
    );
  }

  private isScriptError(error: any): boolean {
    return (
      error?.message?.includes('Script error') ||
      error?.message?.includes('Non-Error promise rejection') ||
      (error instanceof Error && error.name === 'ScriptError')
    );
  }

  private isPromiseRejection(error: any): boolean {
    return (
      error?.rejection !== undefined ||
      error?.promise !== undefined ||
      error?.reason !== undefined
    );
  }

  private handlePromiseRejection(error: any): void {
    const rejectionReason = error.rejection || error.reason || error;

    // If it's an HTTP error in the promise rejection, handle it as such
    if (this.isHttpError(rejectionReason)) {
      this.handleHttpError(rejectionReason);
      return;
    }

    // Otherwise, handle as generic error
    const message = this.getUserFriendlyMessage(rejectionReason);
    this.messageService.showErrorMessage(message, 5000);
  }

  private extractErrorMessage(error: any): string | null {
    // Try multiple paths to extract meaningful error message
    if (error?.error?.details?.error) {
      return error.error.details.error;
    }

    if (error?.error?.message) {
      return error.error.message;
    }

    if (error?.error && typeof error.error === 'string') {
      return error.error;
    }

    if (error?.message && typeof error.message === 'string') {
      return error.message;
    }

    return null;
  }

  private getUserFriendlyMessage(error: any): string {
    // First try to extract a meaningful message
    const extractedMessage = this.extractErrorMessage(error);
    if (extractedMessage) {
      // Transform technical errors to user-friendly messages
      if (
        extractedMessage.includes('Cannot read property') ||
        extractedMessage.includes('Cannot read properties')
      ) {
        return 'Something went wrong. Please try again.';
      }

      if (
        extractedMessage.includes('timeout') ||
        extractedMessage.includes('TIMEOUT')
      ) {
        return 'Request timed out. Please try again.';
      }

      if (
        extractedMessage.includes('Network Error') ||
        extractedMessage.includes('ERR_NETWORK')
      ) {
        return 'Network error. Please check your connection.';
      }

      // Return the extracted message if it seems user-friendly
      if (
        extractedMessage.length < 100 &&
        !extractedMessage.includes('at ') &&
        !extractedMessage.includes('stack')
      ) {
        return extractedMessage;
      }
    }

    return 'An unexpected error occurred. Please try again.';
  }

  private isHandledByInterceptor(error: any): boolean {
    // Check if this error is already handled by the auth interceptor
    if (error?.handledByInterceptor === true) {
      return true;
    }

    // Check for session expired errors
    if (error?.message === 'Session expired') {
      return true;
    }

    // Also check for 401 errors that might bypass the interceptor check
    if (error?.status === 401 && error instanceof HttpErrorResponse) {
      return true;
    }

    return false;
  }

  private isHandledByComponent(error: any): boolean {
    // Check if this error has been marked as handled by a component
    return error?.handledByComponent === true;
  }

  private isUpdateAccountValidationError(error: any): boolean {
    // Check if this is a validation error from the update account endpoint
    const url = error?.url || '';
    const status = error?.status;

    // Skip validation errors from update endpoint - these are handled by components
    if (
      url.includes('/api/users/update') &&
      (status === 409 || status === 400 || status === 422)
    ) {
      return true;
    }

    return false;
  }

  private async sendToMonitoring(error: any): Promise<void> {
    // Enhanced error data for monitoring
    const errorData = {
      timestamp: new Date().toISOString(),
      error: {
        message: error?.message || 'Unknown error',
        stack: error?.stack,
        status: error?.status,
        statusText: error?.statusText,
        url: error?.url || window.location.href,
        userAgent: navigator.userAgent,
        type: this.getErrorType(error),
        originalError: this.sanitizeErrorForLogging(error),
      },
      context: {
        currentUrl: window.location.href,
        userId: this.getCurrentUserId(),
        sessionId: this.getSessionId(),
      },
    };

    try {
      // Send to your Sentry API endpoint
      await fetch(`${Configs.BASE_URL}${Configs.LOG_URL}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          // Add auth header if the endpoint requires authentication
          // 'Authorization': `Bearer ${this.getAuthToken()}`
        },
        body: JSON.stringify(errorData),
      });

      console.log('Error sent to monitoring service');
    } catch (loggingError) {
      // Fallback to console logging if API fails
      console.error(
        'Failed to send error to monitoring service:',
        loggingError
      );
      console.log('Original error data:', errorData);
    }
  }

  private getErrorType(error: any): string {
    if (this.isHttpError(error)) return 'HTTP';
    if (this.isChunkLoadError(error)) return 'CHUNK_LOAD';
    if (this.isScriptError(error)) return 'SCRIPT';
    if (this.isPromiseRejection(error)) return 'PROMISE_REJECTION';
    if (error instanceof TypeError) return 'TYPE_ERROR';
    if (error instanceof ReferenceError) return 'REFERENCE_ERROR';
    if (error instanceof Error) return 'GENERIC_ERROR';
    return 'UNKNOWN';
  }

  private sanitizeErrorForLogging(error: any): any {
    // Remove sensitive data and circular references for logging
    try {
      return JSON.parse(
        JSON.stringify(error, (key, value) => {
          // Remove potential sensitive data
          if (
            key === 'password' ||
            key === 'token' ||
            key === 'authorization'
          ) {
            return '[REDACTED]';
          }
          return value;
        })
      );
    } catch {
      return { message: error?.message || 'Error serialization failed' };
    }
  }

  private getCurrentUserId(): string | null {
    // Extract user ID from local storage or auth service
    try {
      const userStr = localStorage.getItem('auth_user');
      if (userStr) {
        const user = JSON.parse(userStr);
        return user.id || null;
      }
    } catch {
      // Ignore errors
    }
    return null;
  }

  private getSessionId(): string | null {
    // Generate or retrieve session ID for tracking
    try {
      let sessionId = sessionStorage.getItem('session_id');
      if (!sessionId) {
        sessionId =
          Date.now().toString(36) + Math.random().toString(36).slice(2);
        sessionStorage.setItem('session_id', sessionId);
      }
      return sessionId;
    } catch {
      return null;
    }
  }
}
