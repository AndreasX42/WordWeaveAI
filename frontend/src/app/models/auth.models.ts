export interface LoginResponse {
  token: string;
  user: {
    createdAt: string;
    email: string;
    confirmedEmail: boolean;
    id: string;
    isAdmin: boolean;
    profileImage: string;
    username: string;
  };
}

export interface RegisterResponse {
  details: {
    email: string;
    user_id: string;
    username: string;
  };
  message: string;
}

export interface VerifyEmailResponse {
  message: string;
}

export interface ResendCodeResponse {
  message: string;
}

export interface RefreshTokenResponse {
  code: number;
  expire: string;
  token: string;
}

export interface ResetPasswordResponse {
  message: string;
}

export interface DeleteAccountErrorResponse {
  details: {
    error: string;
  };
  message: string;
}
