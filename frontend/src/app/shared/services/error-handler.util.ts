import { Injectable } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';

@Injectable({
  providedIn: 'root',
})
export class ErrorHandlerUtil {
  /**
   * Wraps async operations to ensure proper error propagation to global handler
   */
  static async handleAsyncOperation<T>(
    operation: () => Promise<T>,
    context: string = 'Operation'
  ): Promise<T> {
    try {
      return await operation();
    } catch (error) {
      console.error(`${context} failed:`, error);

      // Ensure the error has proper context for the global handler
      if (error instanceof Error) {
        error.message = `${context}: ${error.message}`;
      }

      throw error;
    }
  }

  /**
   * Wraps synchronous operations that might throw to ensure proper error handling
   */
  static handleSyncOperation<T>(
    operation: () => T,
    context: string = 'Operation'
  ): T {
    try {
      return operation();
    } catch (error) {
      console.error(`${context} failed:`, error);

      // Ensure the error has proper context for the global handler
      if (error instanceof Error) {
        error.message = `${context}: ${error.message}`;
      }

      throw error;
    }
  }

  /**
   * Creates a standardized error for failed operations
   */
  static createOperationError(
    operation: string,
    originalError?: any,
    details?: any
  ): Error {
    const message = `${operation} failed${
      originalError ? ': ' + this.extractErrorMessage(originalError) : ''
    }`;
    const error = new Error(message);

    // Attach additional context
    (error as any).originalError = originalError;
    (error as any).operation = operation;
    (error as any).details = details;

    return error;
  }

  /**
   * Extracts user-friendly error message from various error types
   */
  static extractErrorMessage(error: any): string {
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

    // Object errors
    if (error?.message) {
      return error.message;
    }

    if (error?.error?.message) {
      return error.error.message;
    }

    if (error?.details?.error) {
      return error.details.error;
    }

    return 'Unknown error occurred';
  }

  /**
   * Determines if an error should be handled silently (no user notification)
   */
  static shouldHandleSilently(error: any): boolean {
    // Handle certain errors silently
    const silentErrors = [
      'AbortError', // Cancelled requests
      'User cancelled', // User cancelled operations
      'Navigation cancelled', // Router navigation cancelled
    ];

    const errorMessage = this.extractErrorMessage(error).toLowerCase();
    return silentErrors.some((silent) =>
      errorMessage.includes(silent.toLowerCase())
    );
  }

  /**
   * Creates an enhanced error with operation context
   */
  static enhanceError(
    error: any,
    context: {
      operation?: string;
      component?: string;
      userId?: string;
      attempts?: number;
      maxRetries?: number;
      additional?: any;
    }
  ): Error {
    const message = this.extractErrorMessage(error);
    const enhancedError = new Error(message);

    // Add context information
    Object.assign(enhancedError, {
      originalError: error,
      context,
      timestamp: new Date().toISOString(),
      stack: error?.stack || enhancedError.stack,
    });

    return enhancedError;
  }

  /**
   * Validates response and throws meaningful error if invalid
   */
  static validateResponse<T>(
    response: T | null | undefined,
    operation: string,
    expectedFields?: (keyof T)[]
  ): T {
    if (!response) {
      throw this.createOperationError(
        operation,
        null,
        'Empty response received'
      );
    }

    if (expectedFields && typeof response === 'object') {
      const missingFields = expectedFields.filter(
        (field) => response[field] === undefined || response[field] === null
      );

      if (missingFields.length > 0) {
        throw this.createOperationError(
          operation,
          null,
          `Missing required fields: ${missingFields.join(', ')}`
        );
      }
    }

    return response;
  }

  /**
   * Retry mechanism for operations that might fail temporarily
   */
  static async retryOperation<T>(
    operation: () => Promise<T>,
    options: {
      maxRetries?: number;
      delay?: number;
      context?: string;
      shouldRetry?: (error: any) => boolean;
    } = {}
  ): Promise<T> {
    const {
      maxRetries = 3,
      delay = 1000,
      context = 'Operation',
      shouldRetry = (error) => !this.shouldHandleSilently(error),
    } = options;

    let lastError: any;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error;

        if (attempt === maxRetries || !shouldRetry(error)) {
          console.error(`${context} failed after ${attempt} attempts:`, error);
          throw this.enhanceError(error, {
            operation: context,
            attempts: attempt,
            maxRetries,
          });
        }

        console.warn(
          `${context} attempt ${attempt} failed, retrying in ${delay}ms:`,
          error
        );
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }

    throw lastError;
  }
}
