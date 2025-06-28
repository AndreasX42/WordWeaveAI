import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { User } from '../models/user.model';
import {
  LoginResponse,
  RegisterResponse,
  VerifyEmailResponse,
  ResendCodeResponse,
  RefreshTokenResponse,
  ResetPasswordResponse,
  DeleteAccountErrorResponse,
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
    } catch (error: any) {
      console.error('Login failed:', error);

      // Extract error details
      const errorDetails =
        error?.error?.details?.error || error?.error?.message || '';

      // Handle specific error cases
      if (errorDetails.toLowerCase().includes('invalid credentials')) {
        return false; // Invalid credentials - return false, don't throw
      }

      if (
        errorDetails.toLowerCase().includes('email not confirmed') ||
        errorDetails.toLowerCase().includes('email not verified')
      ) {
        throw new Error('EMAIL_NOT_VERIFIED');
      }

      // For all other errors, throw a generic error
      throw new Error('LOGIN_FAILED');
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
      throw error;
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

  async refreshToken(): Promise<boolean> {
    try {
      const currentToken = this.getAuthToken();

      if (!currentToken) {
        return false;
      }

      const response = await firstValueFrom(
        this.httpClient.post<RefreshTokenResponse>(
          `${Configs.BASE_URL}${Configs.REFRESH_TOKEN_URL}`,
          {},
          {
            headers: {
              Authorization: `Bearer ${currentToken}`,
            },
          }
        )
      );

      if (!response || !response.token) {
        return false;
      }

      // Update the stored token
      localStorage.setItem(this.TOKEN_KEY, response.token);
      return true;
    } catch (error) {
      console.error('Token refresh failed:', error);
      return false;
    }
  }

  async sendPasswordResetEmail(email: string): Promise<boolean> {
    try {
      const response = await firstValueFrom(
        this.httpClient.post<ResetPasswordResponse>(
          `${Configs.BASE_URL}${Configs.RESET_PASSWORD_URL}`,
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
      console.error('Password reset email failed:', error);
      throw error;
    }
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

  async updateAccount(updateData: {
    username: string;
    email: string;
    newPassword?: string;
  }): Promise<boolean> {
    try {
      if (!this.isLoggedIn()) {
        throw new Error('No authentication token found');
      }

      const response = await firstValueFrom(
        this.httpClient.put(
          `${Configs.BASE_URL}${Configs.UPDATE_ACCOUNT_URL}`,
          updateData
        )
      );

      // If update includes email or username, update the local user object
      if (this._user) {
        this._user.username = updateData.username;
        this._user.email = updateData.email;
        localStorage.setItem(this.USER_KEY, JSON.stringify(this._user));
      }

      return true;
    } catch (error: any) {
      console.error('Account update failed:', error);

      // Check if this is a session expired error from the interceptor
      if (error?.message === 'Session expired') {
        // Re-throw the session expired error
        throw error;
      }

      // Extract the specific error message from backend response
      const errorMessage =
        error?.error?.details?.error ||
        error?.error?.message ||
        'Account update failed. Please try again.';

      // Throw an error with the specific message so the component can display it
      throw new Error(errorMessage);
    }
  }

  async deleteAccount(): Promise<void> {
    try {
      if (!this.isLoggedIn()) {
        throw new Error('No authentication token found');
      }

      await firstValueFrom(
        this.httpClient.delete(
          `${Configs.BASE_URL}${Configs.DELETE_ACCOUNT_URL}`
        )
      );

      this.clearAuth();
    } catch (error: any) {
      console.error('Account deletion failed:', error);

      // Check if this is a session expired error from the interceptor
      if (error?.message === 'Session expired') {
        // Re-throw the session expired error
        throw error;
      }

      // Extract the specific error message from backend response for other errors
      const errorMessage =
        error?.error?.details?.error ||
        error?.error?.message ||
        'Account deletion failed. Please try again.';

      // Throw an error with the specific message so the component can display it
      throw new Error(errorMessage);
    }
  }
}
