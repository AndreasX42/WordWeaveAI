import { Injectable, ErrorHandler, inject, NgZone } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { MessageService } from '../../services/message.service';
import { ErrorHandlerUtil } from './error-handler.util';

@Injectable({
  providedIn: 'root',
})
export class GlobalErrorHandler implements ErrorHandler {
  private messageService = inject(MessageService);
  private ngZone = inject(NgZone);

  handleError(error: unknown): void {
    console.error('Global error caught:', error);

    if (this.isHandledByInterceptor(error)) {
      ErrorHandlerUtil.logError(error);
      return;
    }

    if (this.isHandledByComponent(error)) {
      console.log(
        'Error marked as handled by component, skipping global message'
      );
      ErrorHandlerUtil.logError(error);
      return;
    }

    this.ngZone.run(() => {
      if (this.isHttpError(error)) {
        this.handleHttpError(error);
      } else if (this.isChunkLoadError(error)) {
        this.messageService.showErrorMessage('errors.appUpdate');
      } else if (this.isScriptError(error)) {
        this.messageService.showErrorMessage('errors.scriptError');
      } else if (this.isPromiseRejection(error)) {
        this.handlePromiseRejection(error);
      } else {
        this.messageService.showErrorMessage('errors.unexpectedError');
      }
    });

    ErrorHandlerUtil.logError(error);
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

    if (this.isUpdateAccountValidationError(error)) {
      console.log('Global handler: Skipping update account validation error');
      return;
    }

    switch (status) {
      case 0:
        this.messageService.showErrorMessage('errors.network');
        break;

      case 400: {
        this.messageService.showErrorMessage('errors.badRequest');
        break;
      }

      case 401:
        console.log(
          '401 error caught by global handler - should be handled by interceptor'
        );
        break;

      case 403:
        this.messageService.showErrorMessage('errors.forbidden');
        break;

      case 404:
        this.messageService.showErrorMessage('errors.notFound');
        break;

      case 409:
        console.log(
          'Global handler: 409 Conflict - letting component handle it'
        );
        break;

      case 422: {
        this.messageService.showErrorMessage('errors.validation');
        break;
      }

      case 429:
        this.messageService.showWarningMessage('errors.tooManyRequests');
        break;

      case 500:
        this.messageService.showErrorMessage('errors.serverError');
        break;

      case 502:
      case 503:
      case 504:
        this.messageService.showErrorMessage('errors.serviceUnavailable');
        break;

      default: {
        this.messageService.showErrorMessage('errors.requestFailed');
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

    if (this.isHttpError(rejectionReason)) {
      this.handleHttpError(rejectionReason);
      return;
    }

    this.messageService.showErrorMessage('errors.unexpectedError');
  }

  private isHandledByInterceptor(error: unknown): boolean {
    return !!(error as { handledByInterceptor?: boolean }).handledByInterceptor;
  }

  private isHandledByComponent(error: unknown): boolean {
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
}
