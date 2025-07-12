import { Injectable, inject } from '@angular/core';
import {
  HttpRequest,
  HttpHandler,
  HttpEvent,
  HttpInterceptor,
  HttpErrorResponse,
  HttpResponse,
} from '@angular/common/http';
import { Observable, throwError, BehaviorSubject, from } from 'rxjs';
import { catchError, switchMap, filter, take, tap } from 'rxjs/operators';
import { AuthService } from './auth.service';
import { HealthMonitorService } from './health-monitor.service';
import { Configs } from '../shared/config';
import { Router } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  private authService = inject(AuthService);
  private healthService = inject(HealthMonitorService);
  private router = inject(Router);
  private snackBar = inject(MatSnackBar);

  private isRefreshing = false;
  private refreshTokenSubject: BehaviorSubject<string | null> =
    new BehaviorSubject<string | null>(null);

  intercept(
    request: HttpRequest<unknown>,
    next: HttpHandler
  ): Observable<HttpEvent<unknown>> {
    // Track request start time
    const startTime = performance.now();

    // Add auth header for token-based authentication
    const authRequest = this.addAuthHeader(request);

    return next.handle(authRequest).pipe(
      tap((event: HttpEvent<unknown>) => {
        // Track API response time for successful responses
        if (event instanceof HttpResponse) {
          const responseTime = performance.now() - startTime;
          // Only track API calls to our backend, exclude external URLs
          if (request.url.includes(Configs.BASE_URL)) {
            this.healthService.trackApiResponseTime(responseTime);
          }
        }
      }),
      catchError((error: HttpErrorResponse) => {
        // Track API response time even for errors
        if (error.status !== 0) {
          // Exclude network errors (status 0)
          const responseTime = performance.now() - startTime;
          if (request.url.includes(Configs.BASE_URL)) {
            this.healthService.trackApiResponseTime(responseTime);
          }
        }

        // Track API errors for our backend endpoints
        if (request.url.includes(Configs.BASE_URL)) {
          // Track HTTP errors (4xx, 5xx status codes)
          if (error.status >= 400 && error.status < 600) {
            this.healthService.trackApiError();
          }
          // Also track network errors as API errors
          else if (error.status === 0) {
            this.healthService.trackApiError();
          }
        }

        if (error.status === 401 && this.shouldAttemptRefresh(request)) {
          return this.handle401Error(authRequest, next);
        }

        return throwError(() => error);
      })
    );
  }

  private addAuthHeader(request: HttpRequest<unknown>): HttpRequest<unknown> {
    // Don't add auth header to auth endpoints that don't need it
    const authNotRequiredEndpoints = [
      Configs.LOGIN_URL,
      Configs.REGISTER_URL,
      Configs.CONFIRM_EMAIL_URL,
      Configs.RESEND_CODE_URL,
      Configs.RESET_PASSWORD_URL,
      Configs.GOOGLE_LOGIN_URL,
      Configs.GOOGLE_CALLBACK_URL,
      Configs.AUTH_ME_URL,
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

  private shouldAttemptRefresh(request: HttpRequest<unknown>): boolean {
    // Don't attempt refresh if user is not logged in
    if (!this.authService.isLoggedIn()) {
      return false;
    }

    // Don't attempt refresh for the refresh endpoint itself
    if (request.url.includes(Configs.REFRESH_TOKEN_URL)) {
      return false;
    }

    const authEndpoints = [
      Configs.LOGIN_URL,
      Configs.REGISTER_URL,
      Configs.CONFIRM_EMAIL_URL,
      Configs.RESEND_CODE_URL,
      Configs.RESET_PASSWORD_URL,
      Configs.AUTH_ME_URL,
    ];

    return !authEndpoints.some((endpoint) => request.url.includes(endpoint));
  }

  private handle401Error(
    request: HttpRequest<unknown>,
    next: HttpHandler
  ): Observable<HttpEvent<unknown>> {
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
            // Create a more specific error that won't trigger additional user messages
            const sessionError = new Error('Session expired') as Error & {
              handledByInterceptor?: boolean;
            };
            sessionError.handledByInterceptor = true;
            return throwError(() => sessionError);
          }
        }),
        catchError(() => {
          this.isRefreshing = false;
          this.handleSessionExpired();
          // Create a more specific error that won't trigger additional user messages
          const sessionError = new Error('Session expired') as Error & {
            handledByInterceptor?: boolean;
          };
          sessionError.handledByInterceptor = true;
          return throwError(() => sessionError);
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
    this.snackBar.open('Session expired. Please sign in again.', 'Close', {
      duration: 4000,
      panelClass: ['error-snackbar'],
      horizontalPosition: 'center',
      verticalPosition: 'bottom',
    });
    this.router.navigate(['login']);
  }
}
