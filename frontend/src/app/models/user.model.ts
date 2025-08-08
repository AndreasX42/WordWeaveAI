export interface User {
  id: string;
  username: string;
  email: string;
  confirmedEmail: boolean;
  profileImage: string;
  role: string;
  createdAt: Date;
}
