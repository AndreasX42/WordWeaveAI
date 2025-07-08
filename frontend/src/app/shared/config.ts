export class Configs {
  static readonly BASE_URL = 'http://localhost:8080/api';

  // health
  static readonly HEALTH_URL = '/health';

  // search
  static readonly SEARCH_URL = '/search';

  // auth
  static readonly REGISTER_URL = '/auth/register';
  static readonly CONFIRM_EMAIL_URL = '/auth/confirm-email';
  static readonly RESEND_CODE_URL = '/auth/resend-code';
  static readonly RESET_PASSWORD_URL = '/auth/reset-password';
  static readonly GOOGLE_LOGIN_URL = '/auth/google/login';
  static readonly GOOGLE_CALLBACK_URL = '/auth/google/callback';
  static readonly LOGIN_URL = '/auth/login';
  static readonly AUTH_ME_URL = '/auth/me';
  // static readonly LOGOUT_URL = '/auth/logout';
  static readonly REFRESH_TOKEN_URL = '/auth/refresh';

  // users
  static readonly UPDATE_ACCOUNT_URL = '/users/update';
  static readonly DELETE_ACCOUNT_URL = '/users/delete';

  // logging
  static readonly LOG_URL = '/log';
}
