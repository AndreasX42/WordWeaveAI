import { inject, Injectable } from '@angular/core';
import { CanActivate, Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { MessageService } from '../../services/message.service';
import { TranslationService } from '../../services/translation.service';

@Injectable({
  providedIn: 'root',
})
export class AuthGuard implements CanActivate {
  private authService = inject(AuthService);
  private router = inject(Router);
  private messageService = inject(MessageService);
  private translationService = inject(TranslationService);

  canActivate(): boolean {
    if (this.authService.isLoggedIn()) {
      return true;
    } else {
      this.router.navigate(['/login']);
      this.messageService.showWarningMessage(
        this.translationService.translate('messages.sessionExpired')
      );
      return false;
    }
  }
}
