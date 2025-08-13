import { Routes } from '@angular/router';
import { Home } from './pages/home/home';
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
    component: Home,
  },
  {
    path: 'search',
    loadComponent: () =>
      import('./pages/search/search').then((mod) => mod.SearchComponent),
  },
  {
    path: 'words/request',
    loadComponent: () =>
      import('./pages/word-card/word-card').then((mod) => mod.WordCard),
    canActivate: [AuthGuard],
  },
  {
    path: 'words/error',
    loadComponent: () =>
      import('./pages/word-card/word-card').then((mod) => mod.WordCard),
  },
  {
    path: 'words/:sourceLanguage/:targetLanguage/:pos/:word',
    loadComponent: () =>
      import('./pages/word-card/word-card').then((mod) => mod.WordCard),
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
    path: 'forgot-password',
    loadComponent: () =>
      import('./auth/forgot-password/forgot-password').then(
        (mod) => mod.ForgotPassword
      ),
  },
  {
    path: 'auth/callback',
    loadComponent: () =>
      import('./auth/callback/callback').then((mod) => mod.AuthCallback),
  },
  {
    path: 'profile',
    loadComponent: () =>
      import('./auth/profile/profile').then((mod) => mod.Profile),
    canActivate: [AuthGuard],
  },
  {
    path: 'health',
    loadComponent: () =>
      import('./health/health-dashboard').then(
        (mod) => mod.HealthDashboardComponent
      ),
  },
];
