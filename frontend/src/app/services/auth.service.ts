import { HttpClient, HttpResponse } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';
import { Router } from '@angular/router';
import { User } from '../models/user.model';
import { LoginResponse } from '../models/login-response.model';
import { Observable, throwError } from 'rxjs';
import { tap, catchError } from 'rxjs/operators';
import { Configs } from '../shared/config';
import { MessageService } from './message.service';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private readonly localStorageTokenKey = 'auth_token';
  private readonly localStorageUserKey = 'auth_user';

  private _isLoggedIn = signal<boolean>(false);
  private _userToken = signal<string | null>(null);
  private _user = signal<User | null>(null);

  // Public readonly signals
  isLoggedIn = this._isLoggedIn.asReadonly();
  userToken = this._userToken.asReadonly();
  user = this._user.asReadonly();

  private httpClient = inject(HttpClient);
  private router = inject(Router);
  private messageService = inject(MessageService);

  constructor() {
    this.initializeAuthState();
  }

  private initializeAuthState(): void {
    const token = localStorage.getItem(this.localStorageTokenKey);
    const userStr = localStorage.getItem(this.localStorageUserKey);

    if (token && userStr) {
      try {
        const user = JSON.parse(userStr);
        this._isLoggedIn.set(true);
        this._userToken.set(token);
        this._user.set(user);
      } catch (error) {
        // Clear invalid data
        this.clearAuthData();
      }
    }
  }

  login(username: string, password: string): Observable<any> {
    return this.httpClient
      .post<any>(
        `${Configs.BASE_URL}${Configs.LOGIN_URL}`,
        {
          username: username,
          password: password,
        },
        {
          observe: 'response',
        }
      )
      .pipe(
        tap((response: HttpResponse<any>) => {
          const jwtToken: string | null = response.headers.get('Authorization');

          if (!jwtToken) {
            throw new Error(
              'Login failed: JWT token not found in the response.'
            );
          }

          const token = jwtToken.replace('Bearer ', '');

          const body: LoginResponse = response.body;
          const userId: string = body.userId;
          const email: string = body.email;
          const role: string = body.role;

          // Set authentication state
          this._isLoggedIn.set(true);
          this._userToken.set(token);
          this._user.set({
            id: userId,
            username: username,
            email: email,
            profilePicture: '',
            role: role,
          });

          // Store the token and user data in localStorage
          localStorage.setItem(this.localStorageTokenKey, token);
          localStorage.setItem(
            this.localStorageUserKey,
            JSON.stringify(this.user())
          );
        }),
        catchError((error) => {
          let errorMessage = MessageService.MSG_ERROR_UNKOWN;
          if (
            typeof error.error === 'string' &&
            error.error.includes('Incorrect')
          ) {
            errorMessage =
              MessageService.MSG_ERROR_LOGIN_USERNAME_OR_PASSWORD_INCORRECT;
          } else if (error.status === 0) {
            errorMessage = MessageService.MSG_ERROR_NETWORK;
          } else if (error.status >= 500) {
            errorMessage = MessageService.MSG_ERROR_SERVER;
          }

          this.messageService.showErrorModal(errorMessage);
          return throwError(() => new Error(errorMessage));
        })
      );
  }

  logout(): void {
    this.clearAuthData();
    this.router.navigate(['/login'], { replaceUrl: true });
  }

  private clearAuthData(): void {
    localStorage.removeItem(this.localStorageTokenKey);
    localStorage.removeItem(this.localStorageUserKey);
    this._userToken.set(null);
    this._user.set(null);
    this._isLoggedIn.set(false);
  }

  getAuthToken(): string | null {
    return this._userToken();
  }

  isAuthenticated(): boolean {
    return this._isLoggedIn() && !!this._userToken();
  }
}
