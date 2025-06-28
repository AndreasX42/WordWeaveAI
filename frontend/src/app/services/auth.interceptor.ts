import { Injectable, inject } from '@angular/core';
import {
  HttpRequest,
  HttpHandler,
  HttpEvent,
  HttpInterceptor,
  HttpErrorResponse,
} from '@angular/common/http';
import { Observable, throwError, BehaviorSubject, from } from 'rxjs';
import { catchError, switchMap, filter, take } from 'rxjs/operators';
import { AuthService } from './auth.service';
import { MessageService } from './message.service';
import { Configs } from '../shared/config';
import { Router } from '@angular/router';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  private authService = inject(AuthService);
  private messageService = inject(MessageService);
  private router = inject(Router);

  private isRefreshing = false;
  private refreshTokenSubject: BehaviorSubject<any> = new BehaviorSubject<any>(
    null
  );

  intercept(
    request: HttpRequest<unknown>,
    next: HttpHandler
  ): Observable<HttpEvent<unknown>> {
    // Add auth token to requests that need it
    const authRequest = this.addAuthHeader(request);

    return next.handle(authRequest).pipe(
      catchError((error: HttpErrorResponse) => {
        if (error.status === 401 && this.shouldAttemptRefresh(request)) {
          return this.handle401Error(authRequest, next);
        }

        return throwError(() => error);
      })
    );
  }

  private addAuthHeader(request: HttpRequest<any>): HttpRequest<any> {
    // Don't add auth header to auth endpoints that don't need it
    const authNotRequiredEndpoints = [
      Configs.LOGIN_URL,
      Configs.REGISTER_URL,
      Configs.CONFIRM_EMAIL_URL,
      Configs.RESEND_CODE_URL,
      Configs.RESET_PASSWORD_URL,
      Configs.GOOGLE_LOGIN_URL,
      Configs.GOOGLE_CALLBACK_URL,
    ];

    const isAuthNotRequired = authNotRequiredEndpoints.some((endpoint) =>
      request.url.includes(endpoint)
    );

    if (isAuthNotRequired) {
      return request;
    }

    const token = this.authService.getAuthToken();
    if (token) {
      return request.clone({
        setHeaders: {
          Authorization: `Bearer ${token}`,
        },
      });
    }

    return request;
  }

  private shouldAttemptRefresh(request: HttpRequest<any>): boolean {
    // Don't attempt refresh if user is not logged in
    if (!this.authService.isLoggedIn()) {
      return false;
    }

    // Don't attempt refresh for the refresh endpoint itself
    if (request.url.includes(Configs.REFRESH_TOKEN_URL)) {
      return false;
    }

    // Don't attempt refresh for auth endpoints
    const authEndpoints = [
      Configs.LOGIN_URL,
      Configs.REGISTER_URL,
      Configs.CONFIRM_EMAIL_URL,
      Configs.RESEND_CODE_URL,
      Configs.RESET_PASSWORD_URL,
    ];

    return !authEndpoints.some((endpoint) => request.url.includes(endpoint));
  }

  private handle401Error(
    request: HttpRequest<any>,
    next: HttpHandler
  ): Observable<HttpEvent<any>> {
    if (!this.isRefreshing) {
      this.isRefreshing = true;
      this.refreshTokenSubject.next(null);

      return from(this.authService.refreshToken()).pipe(
        switchMap((success) => {
          this.isRefreshing = false;

          if (success) {
            const newToken = this.authService.getAuthToken();
            this.refreshTokenSubject.next(newToken);

            // Retry the original request with the new token
            const newRequest = request.clone({
              setHeaders: {
                Authorization: `Bearer ${newToken}`,
              },
            });

            return next.handle(newRequest);
          } else {
            // Refresh failed, logout and redirect
            this.handleSessionExpired();
            return throwError(() => new Error('Session expired'));
          }
        }),
        catchError(() => {
          this.isRefreshing = false;
          this.handleSessionExpired();
          return throwError(() => new Error('Session expired'));
        })
      );
    } else {
      // If already refreshing, wait for the new token
      return this.refreshTokenSubject.pipe(
        filter((token) => token != null),
        take(1),
        switchMap((token) => {
          const newRequest = request.clone({
            setHeaders: {
              Authorization: `Bearer ${token}`,
            },
          });
          return next.handle(newRequest);
        })
      );
    }
  }

  private handleSessionExpired(): void {
    this.authService.logout();
    this.messageService.showWarningMessage(
      MessageService.MSG_WARNING_SESSION_EXPIRED
    );
    this.router.navigate(['login']);
  }
}
