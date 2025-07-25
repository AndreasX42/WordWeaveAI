import { Component, DestroyRef, inject, signal } from '@angular/core';
import {
  AbstractControl,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatIcon } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { Router, RouterLink } from '@angular/router';
import { ErrorManagerFactory } from '../../shared/error.manager.factory';
import { AuthService } from '../../services/auth.service';
import { MessageService } from '../../services/message.service';
import { TranslationService } from '../../services/translation.service';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { TranslatePipe } from '../../shared/pipes/translate.pipe';

function equalValues(controlName1: string, controlName2: string) {
  return (control: AbstractControl) => {
    const val1 = control.get(controlName1)?.value;
    const val2 = control.get(controlName2)?.value;

    if (val1 === val2) {
      return null;
    }

    const errorMessage = { valuesNotEqual: true };
    if (controlName2 === 'confirmPassword') {
      control.get(controlName2)?.setErrors(errorMessage);
    }

    return { valuesNotEqual: true };
  };
}

function strictEmailValidator(control: AbstractControl) {
  const email = control.value;
  if (!email) {
    return null;
  }

  // More strict email pattern that requires proper domain
  const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

  if (!emailPattern.test(email)) {
    return { invalidEmail: true };
  }

  return null;
}

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [
    MatButtonModule,
    MatInputModule,
    MatFormFieldModule,
    MatIcon,
    ReactiveFormsModule,
    RouterLink,
    MatProgressSpinner,
    CommonModule,
    MatCardModule,
    TranslatePipe,
  ],
  templateUrl: './register.html',
  styleUrl: './register.scss',
})
export class Register {
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
  private authService = inject(AuthService);
  private messageService = inject(MessageService);
  private translationService = inject(TranslationService);

  hide = signal(true);
  isRegistering = signal(false);
  usernameErrorMessage = signal<string>('');
  emailErrorMessage = signal<string>('');
  pwdErrorMessage = signal<string>('');
  confirmPwdErrorMessage = signal<string>('');

  form = new FormGroup({
    username: new FormControl('', {
      validators: [Validators.required, Validators.minLength(3)],
    }),
    email: new FormControl('', {
      validators: [Validators.required, strictEmailValidator],
    }),
    passwords: new FormGroup(
      {
        password: new FormControl('', {
          validators: [Validators.required, Validators.minLength(8)],
        }),
        confirmPassword: new FormControl('', {
          validators: [Validators.required, Validators.minLength(8)],
        }),
      },
      {
        validators: [equalValues('password', 'confirmPassword')],
      }
    ),
  });

  constructor() {
    // If already logged in, redirect to home
    if (this.authService.isLoggedIn()) {
      this.router.navigate(['/home'], { replaceUrl: true });
    }
  }

  onSubmit() {
    if (this.form.invalid) {
      // Update error messages for all form fields
      this.updateUsernameErrorMessage();
      this.updateEmailErrorMessage();
      this.updatePwdErrorMessage();
      this.updateConfirmPwdErrorMessage();
      return;
    }

    const username = this.form.value.username!;
    const email = this.form.value.email!;
    const password = this.form.value.passwords!.password!;

    this.register(username, email, password);
  }

  private async register(username: string, email: string, password: string) {
    this.isRegistering.set(true);

    try {
      await this.authService.register(username, email, password);

      // If we reach here, registration was successful
      this.isRegistering.set(false);
      this.messageService.showSuccessMessage(
        this.translationService.translate('auth.registrationSuccessful'),
        5000
      );
      // Redirect to verification page with email as query parameter
      this.router.navigate(['/verify'], {
        queryParams: { email: email },
        replaceUrl: true,
      });
    } catch (error) {
      this.isRegistering.set(false);

      // Check for specific backend error messages
      const errorObj = error as {
        error?: {
          details?: { error?: string };
          message?: string;
        };
      };
      const backendError =
        errorObj?.error?.details?.error || errorObj?.error?.message || '';
      const isUsernameExists = backendError
        .toLowerCase()
        .includes('username already exists');
      const isEmailExists = backendError
        .toLowerCase()
        .includes('email already exists');

      let errorMessage = this.translationService.translate(
        'auth.registrationFailed'
      );

      if (isUsernameExists || isEmailExists) {
        errorMessage = this.translationService.translate(
          'auth.usernameOrEmailExists'
        );
      }

      this.messageService.showErrorMessage(errorMessage);
    }
  }

  onHide(event: MouseEvent) {
    this.hide.set(!this.hide());
    event.stopPropagation();
  }

  updateUsernameErrorMessage = ErrorManagerFactory.getFormErrorManager(
    this.form.get('username')!,
    this.usernameErrorMessage.set,
    {
      required: ErrorManagerFactory.MSG_IS_REQUIRED,
      minlength: ErrorManagerFactory.MSG_AT_LEAST_3_CHARS,
    }
  );

  updateEmailErrorMessage = ErrorManagerFactory.getFormErrorManager(
    this.form.get('email')!,
    this.emailErrorMessage.set,
    {
      required: ErrorManagerFactory.MSG_IS_REQUIRED,
      invalidEmail: ErrorManagerFactory.MSG_VALID_EMAIL,
    }
  );

  updatePwdErrorMessage = ErrorManagerFactory.getFormErrorManager(
    this.form.controls.passwords.get('password')!,
    this.pwdErrorMessage.set,
    {
      required: ErrorManagerFactory.MSG_IS_REQUIRED,
      minlength: ErrorManagerFactory.MSG_AT_LEAST_8_CHARS,
    }
  );

  updateConfirmPwdErrorMessage = ErrorManagerFactory.getFormErrorManager(
    this.form.controls.passwords.get('confirmPassword')!,
    this.confirmPwdErrorMessage.set,
    {
      required: ErrorManagerFactory.MSG_IS_REQUIRED,
      minlength: ErrorManagerFactory.MSG_AT_LEAST_8_CHARS,
      valuesNotEqual: 'Passwords must match',
    }
  );
}
