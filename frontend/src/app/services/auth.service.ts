import { Injectable, inject, computed, signal } from '@angular/core';
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
} from '../models/auth.models';
import { Configs } from '../shared/config';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private readonly TOKEN_KEY = 'auth_token';
  private readonly USER_KEY = 'auth_user';

  // Convert to signals for better reactivity
  private _isLoggedIn = signal<boolean>(false);
  private _user = signal<User | null>(null);

  // Public computed signals
  public isLoggedIn = computed(() => this._isLoggedIn());
  public user = computed(() => this._user());

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
        this._isLoggedIn.set(true);
        this._user.set(user);
      }
    } catch {
      // If anything fails, just stay logged out
      this.clearAuth();
    }
  }

  async login(email: string, password: string): Promise<boolean> {
    try {
      const response = await firstValueFrom(
        this.httpClient.post<LoginResponse>(
          `${Configs.BASE_URL}${Configs.LOGIN_URL}`,
          {
            email: email,
            password: password,
          },
          { withCredentials: true }
        )
      );

      if (!response || !response.token || !response.user) {
        return false;
      }

      const token = response.token;
      const apiUser = response.user;

      // Create user object
      const user: User = {
        id: apiUser.id,
        username: apiUser.username,
        email: apiUser.email,
        confirmedEmail: apiUser.confirmedEmail,
        profileImage: apiUser.profileImage || '',
        role: apiUser.isAdmin ? 'admin' : 'user',
        createdAt: new Date(apiUser.createdAt),
      };

      // Set authentication state
      this._isLoggedIn.set(true);
      this._user.set(user);

      // Store in localStorage
      localStorage.setItem(this.TOKEN_KEY, token);
      localStorage.setItem(this.USER_KEY, JSON.stringify(user));

      return true;
    } catch (error) {
      console.error('Login failed:', error);

      // Extract error details safely
      const httpError = error as {
        error?: { details?: { error?: string }; message?: string };
      };
      const errorDetails =
        httpError?.error?.details?.error || httpError?.error?.message || '';

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
        throw new Error('Invalid registration response from server');
      }

      return true;
    } catch (error) {
      console.error('Registration failed:', error);
      // Re-throw to allow global error handler to process it
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
        throw new Error('Invalid verification response from server');
      }

      return true;
    } catch (error) {
      console.error('Email verification failed:', error);
      // Re-throw to allow global error handler to process it
      throw error;
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
        throw new Error('Failed to resend verification code');
      }

      return true;
    } catch (error) {
      console.error('Resend verification code failed:', error);
      // Re-throw to allow global error handler to process it
      throw error;
    }
  }

  async refreshToken(): Promise<string | null> {
    try {
      const currentToken = this.getAuthToken();

      if (!currentToken) {
        return null;
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
        return null;
      }

      localStorage.setItem(this.TOKEN_KEY, response.token);
      return response.token;
    } catch (error) {
      console.error('Token refresh failed:', error);
      return null;
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

  googleLogin(): void {
    // Redirect to backend Google OAuth endpoint to start the OAuth flow
    window.location.href = `${Configs.BASE_URL}${Configs.GOOGLE_LOGIN_URL}`;
  }

  async authenticateWithOAuth(): Promise<boolean> {
    try {
      // Call /api/auth/me endpoint
      const response = await firstValueFrom(
        this.httpClient.get<LoginResponse>(
          `${Configs.BASE_URL}${Configs.AUTH_ME_URL}`,
          {
            withCredentials: true, // Include cookies in request
          }
        )
      );

      if (!response || !response.user || !response.token) {
        return false;
      }

      const userData = response.user;

      // Create user object from response
      const user: User = {
        id: userData.id,
        username: userData.username,
        email: userData.email,
        confirmedEmail: userData.confirmedEmail || true,
        profileImage: userData.profileImage || '',
        role: userData.isAdmin ? 'admin' : 'user',
        createdAt: new Date(userData.createdAt),
      };

      // Store the JWT token for future API requests
      localStorage.setItem(this.TOKEN_KEY, response.token);

      // Set authentication state
      this._isLoggedIn.set(true);
      this._user.set(user);

      // Store user in localStorage
      localStorage.setItem(this.USER_KEY, JSON.stringify(user));

      return true;
    } catch (error) {
      console.error('Failed to authenticate with OAuth:', error);
      return false;
    }
  }

  logout(): void {
    this.clearAuth();
  }

  getAuthToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }

  private clearAuth(): void {
    this._isLoggedIn.set(false);
    this._user.set(null);
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

      await firstValueFrom(
        this.httpClient.put(
          `${Configs.BASE_URL}${Configs.UPDATE_ACCOUNT_URL}`,
          updateData
        )
      );

      // If update includes email or username, update the local user object
      const currentUser = this._user();
      if (currentUser) {
        this._user.set({
          ...currentUser,
          username: updateData.username,
          email: updateData.email,
        });
        localStorage.setItem(this.USER_KEY, JSON.stringify(this._user()));
      }

      return true;
    } catch (error) {
      console.error('Account update failed:', error);

      // Check if this is a session expired error from the interceptor
      if ((error as Error)?.message === 'Session expired') {
        // Re-throw the session expired error
        throw error;
      }

      // Preserve the original HTTP error structure for the dialog to handle
      // Mark it as handled by component to prevent global error handler from showing messages
      (error as { handledByComponent?: boolean }).handledByComponent = true;

      throw error;
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
    } catch (error) {
      console.error('Account deletion failed:', error);

      // Check if this is a session expired error from the interceptor
      if ((error as Error)?.message === 'Session expired') {
        // Re-throw the session expired error
        throw error;
      }

      // Preserve the original HTTP error structure for the component to handle
      // Mark it as handled by component to prevent global error handler from showing messages
      (error as { handledByComponent?: boolean }).handledByComponent = true;

      throw error;
    }
  }
}
