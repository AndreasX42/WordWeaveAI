export class Configs {
  static readonly BASE_URL = 'http://localhost:8080/api';

  // auth
  static readonly REGISTER_URL = '/auth/register';
  static readonly CONFIRM_EMAIL_URL = '/auth/confirm-email';
  static readonly RESEND_CODE_URL = '/auth/resend-code';
  static readonly RESET_PASSWORD_URL = '/auth/reset-password';
  static readonly GOOGLE_LOGIN_URL = '/auth/google/login';
  static readonly GOOGLE_CALLBACK_URL = '/auth/google/callback';
  static readonly LOGIN_URL = '/auth/login';
  // static readonly LOGOUT_URL = '/auth/logout';
  static readonly REFRESH_TOKEN_URL = '/auth/refresh';

  // users
  static readonly UPDATE_ACCOUNT_URL = '/users/update';
  static readonly DELETE_ACCOUNT_URL = '/users/delete';
}
