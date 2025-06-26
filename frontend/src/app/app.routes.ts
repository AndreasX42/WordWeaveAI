import { Routes } from '@angular/router';
import { canLeaveEditPage } from './shared/guards/leave.guard';
import { AuthGuard } from './shared/guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    redirectTo: '/home',
    pathMatch: 'full',
  },
  {
    path: 'home',
    loadComponent: () => import('./pages/home/home').then((mod) => mod.Home),
  },
  {
    path: 'login',
    loadComponent: () => import('./auth/login/login').then((mod) => mod.Login),
  },
  {
    path: 'register',
    loadComponent: () =>
      import('./auth/register/register').then((mod) => mod.Register),
    canDeactivate: [canLeaveEditPage],
  },
  {
    path: 'verify',
    loadComponent: () =>
      import('./auth/verify/verify').then((mod) => mod.Verify),
  },
  {
    path: 'profile',
    loadComponent: () =>
      import('./auth/profile/profile').then((mod) => mod.Profile),
    canActivate: [AuthGuard],
  },
];
