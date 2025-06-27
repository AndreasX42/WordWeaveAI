import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { User } from '../models/user.model';
import {
  LoginResponse,
  RegisterResponse,
  VerifyEmailResponse,
  ResendCodeResponse,
} from '../models/auth.models';
import { Configs } from '../shared/config';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private readonly TOKEN_KEY = 'auth_token';
  private readonly USER_KEY = 'auth_user';

  private _isLoggedIn: boolean = false;
  private _user: User | null = null;
  private httpClient = inject(HttpClient);

  constructor() {
    // Safe initialization without breaking signals
    this.loadFromStorage();
  }

  private loadFromStorage(): void {
    try {
      const token = localStorage.getItem(this.TOKEN_KEY);
      const userStr = localStorage.getItem(this.USER_KEY);

      if (token && userStr) {
        const user = JSON.parse(userStr);
        this._isLoggedIn = true;
        this._user = user;
      }
    } catch (error) {
      // If anything fails, just stay logged out
      this.clearAuth();
    }
  }

  isLoggedIn(): boolean {
    return this._isLoggedIn;
  }

  user(): User | null {
    return this._user;
  }

  async login(email: string, password: string): Promise<boolean> {
    try {
      const response = await firstValueFrom(
        this.httpClient.post<LoginResponse>(
          `${Configs.BASE_URL}${Configs.LOGIN_URL}`,
          {
            email: email,
            password: password,
          }
        )
      );

      if (!response || !response.token || !response.details?.user) {
        return false;
      }

      const token = response.token;
      const apiUser = response.details.user;

      // Create user object
      const user: User = {
        id: apiUser.id,
        username: apiUser.username,
        email: apiUser.email,
        profilePicture: apiUser.profileImage || '',
        role: apiUser.isAdmin ? 'admin' : 'user',
      };

      // Set authentication state
      this._isLoggedIn = true;
      this._user = user;

      // Store in localStorage
      localStorage.setItem(this.TOKEN_KEY, token);
      localStorage.setItem(this.USER_KEY, JSON.stringify(user));

      return true;
    } catch (error) {
      console.error('Login failed:', error);
      return false;
    }
  }

  async register(
    username: string,
    email: string,
    password: string
  ): Promise<boolean> {
    try {
      const response = await firstValueFrom(
        this.httpClient.post<RegisterResponse>(
          `${Configs.BASE_URL}${Configs.REGISTER_URL}`,
          {
            username: username,
            email: email,
            password: password,
          }
        )
      );

      if (!response || !response.details?.user_id) {
        return false;
      }

      return true;
    } catch (error) {
      console.error('Registration failed:', error);
      return false;
    }
  }

  async verifyEmail(email: string, code: string): Promise<boolean> {
    try {
      const response = await firstValueFrom(
        this.httpClient.post<VerifyEmailResponse>(
          `${Configs.BASE_URL}${Configs.CONFIRM_EMAIL_URL}`,
          {
            email: email,
            code: code,
          }
        )
      );

      if (!response || !response.message) {
        return false;
      }

      return true;
    } catch (error) {
      console.error('Email verification failed:', error);
      return false;
    }
  }

  async resendVerificationCode(email: string): Promise<boolean> {
    try {
      const response = await firstValueFrom(
        this.httpClient.post<ResendCodeResponse>(
          `${Configs.BASE_URL}${Configs.RESEND_CODE_URL}`,
          {
            email: email,
          }
        )
      );

      if (!response || !response.message) {
        return false;
      }

      return true;
    } catch (error) {
      console.error('Resend verification code failed:', error);
      return false;
    }
  }

  sendPasswordResetEmail(email: string): Promise<boolean> {
    return new Promise((resolve) => {
      // TODO: Replace with actual API call to send password reset email
      resolve(false);
    });
  }

  googleLogin(): Promise<boolean> {
    return new Promise((resolve) => {
      // TODO: Implement Google OAuth login
      // This would typically involve:
      // 1. Initialize Google OAuth client
      // 2. Handle OAuth flow
      // 3. Get user data from Google
      // 4. Authenticate with backend
      // 5. Store user session
      resolve(false);
    });
  }

  logout(): void {
    this.clearAuth();
  }

  getAuthToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }

  private clearAuth(): void {
    this._isLoggedIn = false;
    this._user = null;
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
  }
}
