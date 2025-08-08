import { Injectable } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { Configs } from '../config';

@Injectable({
  providedIn: 'root',
})
export class ErrorHandlerUtil {
  private static lastLogTime = 0;

  static logError(error: unknown, message?: string): void {
    const errorData = this.buildErrorPayload(error, 'ERROR', message);
    this.sendToMonitoring(errorData);
  }

  static logWarning(message: string): void {
    const errorData = this.buildErrorPayload(message, 'WARNING', message);
    this.sendToMonitoring(errorData);
  }

  private static buildErrorPayload(
    error: unknown,
    level: 'ERROR' | 'WARNING',
    message?: string
  ) {
    const sanitizedError = this.sanitizeErrorForLogging(error);
    const errorWithMessage = sanitizedError as {
      message?: string;
      stack?: string;
      status?: number;
      statusText?: string;
      url?: string;
    };

    return {
      timestamp: new Date().toISOString(),
      level,
      message: message || errorWithMessage?.message || 'Unknown error',
      error: {
        status: errorWithMessage?.status,
        statusText: errorWithMessage?.statusText,
        url: errorWithMessage?.url || window.location.href,
        userAgent: navigator.userAgent,
        type: message || this.getErrorType(error),
        originalError: sanitizedError,
      },
      context: {
        currentUrl: window.location.href,
        userId: this.getCurrentUserId(),
        sessionId: this.getSessionId(),
      },
    };
  }

  private static async sendToMonitoring(errorData: unknown): Promise<void> {
    const now = Date.now();
    if (now - this.lastLogTime < 1000) {
      console.warn('Duplicate log suppressed to prevent loop.');
      return;
    }
    this.lastLogTime = now;

    try {
      await fetch(`${Configs.BASE_URL}${Configs.LOG_URL}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(errorData),
      });
      console.log('Log sent to monitoring service');
    } catch (loggingError) {
      console.error('Failed to send log to monitoring service:', loggingError);
      console.log('Original log data:', errorData);
    }
  }

  private static getErrorType(error: unknown): string {
    if (error instanceof TypeError) return 'TYPE_ERROR';
    if (error instanceof ReferenceError) return 'REFERENCE_ERROR';
    if (error instanceof Error) return 'GENERIC_ERROR';
    return 'UNKNOWN';
  }

  private static sanitizeErrorForLogging(error: unknown): unknown {
    if (error instanceof Error) {
      // Trim the stack trace to only include the most relevant entries
      let stack = error.stack || '';
      if (stack) {
        const stackLines = stack.split('\n');
        // Keep only the first 10 lines (error message + 9 stack entries)
        const trimmedStack = stackLines.slice(0, 10).join('\n');
        stack =
          trimmedStack +
          (stackLines.length > 10 ? '\n    ... (truncated)' : '');
      }

      return {
        message: error.message,
        stack,
        name: error.name,
      };
    }

    try {
      return JSON.parse(
        JSON.stringify(error, (key, value) => {
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

  private static getCurrentUserId(): string | null {
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

  private static getSessionId(): string | null {
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

  /**
   * Extracts user-friendly error message from various error types
   */
  static extractErrorMessage(error: unknown): string {
    if (!error) return 'Unknown error';

    // HTTP errors
    if (error instanceof HttpErrorResponse) {
      return (
        error.error?.message ||
        error.error?.details?.error ||
        error.message ||
        `HTTP ${error.status} Error`
      );
    }

    // Standard errors
    if (error instanceof Error) {
      return error.message;
    }

    // String errors
    if (typeof error === 'string') {
      return error;
    }

    // Object errors with safe property access
    const errorObj = error as Record<string, unknown>;
    if (errorObj?.['message'] && typeof errorObj['message'] === 'string') {
      return errorObj['message'];
    }

    const errorProp = errorObj?.['error'] as Record<string, unknown>;
    if (errorProp?.['message'] && typeof errorProp['message'] === 'string') {
      return errorProp['message'];
    }

    const detailsProp = errorObj?.['details'] as Record<string, unknown>;
    if (detailsProp?.['error'] && typeof detailsProp['error'] === 'string') {
      return detailsProp['error'];
    }

    return 'Unknown error occurred';
  }
}
