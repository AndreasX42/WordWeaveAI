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
  private lastErrorTime = 0;

  handleError(error: unknown): void {
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

  private isHttpError(error: unknown): boolean {
    return (
      error instanceof HttpErrorResponse ||
      ((error as { status?: unknown })?.status !== undefined &&
        typeof (error as { status: unknown }).status === 'number')
    );
  }

  private handleHttpError(error: HttpErrorResponse | unknown): void {
    const status = (error as { status?: number }).status || 0;

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

      case 400: {
        // Bad request
        const badRequestMessage =
          this.extractErrorMessage(error) ||
          'Please check your input and try again.';
        this.messageService.showErrorMessage(badRequestMessage, 4000);
        break;
      }

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

      case 422: {
        // Validation error
        const validationMessage =
          this.extractErrorMessage(error) ||
          'Please check your input and try again.';
        this.messageService.showErrorMessage(validationMessage, 4000);
        break;
      }

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

      default: {
        // Generic HTTP error
        const genericMessage =
          this.extractErrorMessage(error) ||
          `Request failed (${status}). Please try again.`;
        this.messageService.showErrorMessage(genericMessage, 5000);
      }
    }
  }

  private isChunkLoadError(error: unknown): boolean {
    const message = (error as { message?: string })?.message;
    return Boolean(
      message?.includes('Loading chunk') ||
        message?.includes('Loading CSS chunk') ||
        message?.includes('ChunkLoadError')
    );
  }

  private isScriptError(error: unknown): boolean {
    const message = (error as { message?: string })?.message;
    return (
      message?.includes('Script error') ||
      message?.includes('Non-Error promise rejection') ||
      (error instanceof Error && error.name === 'ScriptError')
    );
  }

  private isPromiseRejection(error: unknown): boolean {
    const errorObj = error as {
      rejection?: unknown;
      promise?: unknown;
      reason?: unknown;
    };
    return (
      errorObj?.rejection !== undefined ||
      errorObj?.promise !== undefined ||
      errorObj?.reason !== undefined
    );
  }

  private handlePromiseRejection(error: unknown): void {
    const errorObj = error as { rejection?: unknown; reason?: unknown };
    const rejectionReason = errorObj.rejection || errorObj.reason || error;

    // If it's an HTTP error in the promise rejection, handle it as such
    if (this.isHttpError(rejectionReason)) {
      this.handleHttpError(rejectionReason);
      return;
    }

    // Otherwise, handle as generic error
    const message = this.getUserFriendlyMessage(rejectionReason);
    this.messageService.showErrorMessage(message, 5000);
  }

  private extractErrorMessage(error: unknown): string | null {
    // Try multiple paths to extract meaningful error message
    const errorObj = error as {
      error?: { details?: { error?: string }; message?: string };
      message?: string;
    };

    if (errorObj?.error?.details?.error) {
      return errorObj.error.details.error;
    }

    if (errorObj?.error?.message) {
      return errorObj.error.message;
    }

    if (
      (errorObj as { error?: unknown }).error &&
      typeof (errorObj as { error: unknown }).error === 'string'
    ) {
      return (errorObj as { error: string }).error;
    }

    if (errorObj?.message && typeof errorObj.message === 'string') {
      return errorObj.message;
    }

    return null;
  }

  private getUserFriendlyMessage(error: unknown): string {
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

  private isHandledByInterceptor(error: unknown): boolean {
    // Look for a specific property that the interceptor adds
    return !!(error as { handledByInterceptor?: boolean }).handledByInterceptor;
  }

  private isHandledByComponent(error: unknown): boolean {
    // Check if this error has been marked as a handled by component
    return (
      (error as { handledByComponent?: boolean })?.handledByComponent === true
    );
  }

  private isUpdateAccountValidationError(error: unknown): boolean {
    const errorObj = error as { url?: string; status?: number };
    return !!(
      errorObj.url?.includes('/update-account') && errorObj.status === 409
    );
  }

  private async sendToMonitoring(error: unknown): Promise<void> {
    // Debounce to prevent infinite loops
    const now = Date.now();
    if (now - this.lastErrorTime < 1000) {
      console.warn('Duplicate error suppressed from logging to prevent loop.');
      return;
    }
    this.lastErrorTime = now;

    // Sanitize and collect error details
    const sanitizedError = this.sanitizeErrorForLogging(error);
    const errorType = this.getErrorType(sanitizedError);

    const errorWithMessage = sanitizedError as {
      message?: string;
      stack?: string;
      status?: number;
      statusText?: string;
      url?: string;
    };

    const context: Record<string, unknown> = {
      currentUrl: window.location.href,
      userId: this.getCurrentUserId(),
      sessionId: this.getSessionId(),
    };

    // Enhanced error data for monitoring
    const errorData = {
      timestamp: new Date().toISOString(),
      error: {
        message: errorWithMessage?.message || 'Unknown error',
        stack: errorWithMessage?.stack,
        status: errorWithMessage?.status,
        statusText: errorWithMessage?.statusText,
        url: errorWithMessage?.url || window.location.href,
        userAgent: navigator.userAgent,
        type: errorType,
        originalError: sanitizedError,
      },
      context,
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

  private getErrorType(error: unknown): string {
    if (this.isHttpError(error)) return 'HTTP';
    if (this.isChunkLoadError(error)) return 'CHUNK_LOAD';
    if (this.isScriptError(error)) return 'SCRIPT';
    if (this.isPromiseRejection(error)) return 'PROMISE_REJECTION';
    if (error instanceof TypeError) return 'TYPE_ERROR';
    if (error instanceof ReferenceError) return 'REFERENCE_ERROR';
    if (error instanceof Error) return 'GENERIC_ERROR';
    return 'UNKNOWN';
  }

  private sanitizeErrorForLogging(error: unknown): unknown {
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
      return {
        message:
          (error as { message?: string })?.message ||
          'Error serialization failed',
      };
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
