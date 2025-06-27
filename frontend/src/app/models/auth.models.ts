export interface LoginResponse {
  code: number;
  expire: string;
  token: string;
  details: {
    user: {
      createdAt: string;
      email: string;
      id: string;
      isAdmin: boolean;
      profileImage: string;
      username: string;
    };
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
