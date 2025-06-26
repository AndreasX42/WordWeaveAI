import { Injectable } from '@angular/core';
import { User } from '../models/user.model';

@Injectable({
  providedIn: 'root',
})
export class SimpleAuthService {
  private readonly TOKEN_KEY = 'auth_token';
  private readonly USER_KEY = 'auth_user';

  private _isLoggedIn: boolean = false;
  private _user: User | null = null;

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

  login(email: string, password: string): Promise<boolean> {
    return new Promise((resolve) => {
      // TODO: Replace with actual API call using email and password
      resolve(false);
    });
  }

  register(
    username: string,
    email: string,
    password: string
  ): Promise<boolean> {
    return new Promise((resolve) => {
      // TODO: Replace with actual API call that sends verification email
      resolve(false);
    });
  }

  verifyEmail(email: string, code: string): Promise<boolean> {
    return new Promise((resolve) => {
      // TODO: Replace with actual API call to verify email
      resolve(false);
    });
  }

  resendVerificationCode(email: string): Promise<boolean> {
    return new Promise((resolve) => {
      // TODO: Replace with actual API call to resend verification code
      resolve(false);
    });
  }

  sendPasswordResetEmail(email: string): Promise<boolean> {
    return new Promise((resolve) => {
      // TODO: Replace with actual API call to send password reset email
      resolve(false);
    });
  }

  logout(): void {
    this.clearAuth();
  }

  private clearAuth(): void {
    this._isLoggedIn = false;
    this._user = null;
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
  }
}
