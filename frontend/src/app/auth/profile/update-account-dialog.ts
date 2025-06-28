import { Component, inject, signal } from '@angular/core';
import {
  MatDialogRef,
  MAT_DIALOG_DATA,
  MatDialogModule,
} from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import {
  AbstractControl,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../services/auth.service';
import { MessageService } from '../../services/message.service';
import { ErrorManagerFactory } from '../../shared/error.manager.factory';

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
  selector: 'app-update-account-dialog',
  standalone: true,
  imports: [
    MatDialogModule,
    MatButtonModule,
    MatInputModule,
    MatFormFieldModule,
    MatIconModule,
    ReactiveFormsModule,
    CommonModule,
  ],
  template: `
    <h2 mat-dialog-title>Update Account</h2>
    <mat-dialog-content>
      <form [formGroup]="form" class="update-form">
        <!-- Username field -->
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Username</mat-label>
          <input
            matInput
            formControlName="username"
            (blur)="updateUsernameErrorMessage()"
          />

          <!-- Success icon when valid -->
          @if(usernameErrorMessage() === '' && form.get('username')?.value &&
          form.get('username')?.valid) {
          <mat-icon matIconSuffix class="success-icon">check_circle</mat-icon>
          } @else {
          <mat-icon matIconSuffix>person</mat-icon>
          }

          <!-- Error message -->
          @if(usernameErrorMessage() !== '') {
          <mat-error>{{ usernameErrorMessage() }}</mat-error>
          }
        </mat-form-field>

        <!-- Email field -->
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Email</mat-label>
          <input
            matInput
            formControlName="email"
            type="email"
            (blur)="updateEmailErrorMessage()"
          />

          <!-- Success icon when valid -->
          @if(emailErrorMessage() === '' && form.get('email')?.value &&
          form.get('email')?.valid) {
          <mat-icon matIconSuffix class="success-icon">check_circle</mat-icon>
          } @else {
          <mat-icon matIconSuffix>email</mat-icon>
          }

          <!-- Error message -->
          @if(emailErrorMessage() !== '') {
          <mat-error>{{ emailErrorMessage() }}</mat-error>
          }
        </mat-form-field>

        <!-- Password field -->
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Password (optional)</mat-label>
          <input
            matInput
            formControlName="password"
            [type]="hidePassword() ? 'password' : 'text'"
            (blur)="updatePasswordErrorMessage()"
          />

          <!-- Success icon when valid -->
          @if(passwordErrorMessage() === '' && form.get('password')?.value &&
          form.get('password')?.valid) {
          <mat-icon matIconSuffix class="success-icon">check_circle</mat-icon>
          }

          <!-- Password visibility toggle -->
          <mat-icon
            matIconSuffix
            (click)="togglePasswordVisibility()"
            style="cursor: pointer;"
            class="password-toggle"
          >
            {{ hidePassword() ? 'visibility_off' : 'visibility' }}
          </mat-icon>

          <!-- Error message -->
          @if(passwordErrorMessage() !== '') {
          <mat-error>{{ passwordErrorMessage() }}</mat-error>
          }
        </mat-form-field>
      </form>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button (click)="onCancel()">Cancel</button>
      <button
        mat-raised-button
        color="primary"
        (click)="onSave()"
        [disabled]="isUpdating() || form.invalid || !hasFormChanges()"
      >
        {{ isUpdating() ? 'Updating...' : 'Update Account' }}
      </button>
    </mat-dialog-actions>
  `,
  styles: [
    `
      ::ng-deep .mat-mdc-dialog-surface {
        background-color: var(--card-background, #ffffff) !important;
        color: var(--text-primary, #333333) !important;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15),
          0 4px 20px rgba(0, 0, 0, 0.08), 0 2px 8px rgba(0, 0, 0, 0.05);
        border-radius: 16px;
        border: 1px solid var(--border-color, rgba(0, 0, 0, 0.06));
      }

      ::ng-deep .mat-mdc-dialog-title {
        color: var(--text-primary, #333333) !important;
        font-size: 24px;
        font-weight: 600;
        margin-bottom: 8px;
      }

      .update-form {
        display: flex;
        flex-direction: column;
        gap: 20px;
        min-width: 280px;
        width: 100%;
      }

      .full-width {
        width: 100%;

        .mat-mdc-form-field-subscript-wrapper {
          margin-top: 8px;
        }

        .success-icon {
          color: #4caf50 !important;
        }

        .password-toggle {
          cursor: pointer;
        }
      }

      /* Light mode input styling - more specific selectors */
      @media (prefers-color-scheme: light),
        (prefers-color-scheme: no-preference) {
        ::ng-deep .full-width input {
          color: #333333 !important;
        }

        ::ng-deep .full-width input::placeholder {
          color: #666666 !important;
          opacity: 0.7;
        }

        ::ng-deep .full-width .mat-mdc-form-field-infix input {
          color: #333333 !important;
        }

        ::ng-deep .full-width .mat-mdc-form-field-label {
          color: #666666 !important;
        }

        ::ng-deep .full-width .mat-mdc-floating-label {
          color: #666666 !important;
        }

        ::ng-deep
          .full-width
          .mat-mdc-floating-label.mdc-floating-label--float-above {
          color: #1976d2 !important;
        }

        ::ng-deep .full-width .mat-icon {
          color: #666666 !important;
        }
      }

      /* Default light mode styles (fallback) */
      :host:not(.dark-theme) ::ng-deep .full-width input {
        color: #333333 !important;
      }

      :host:not(.dark-theme)
        ::ng-deep
        .full-width
        .mat-mdc-form-field-infix
        input {
        color: #333333 !important;
      }

      mat-dialog-content {
        padding: 24px !important;
      }

      @media (max-width: 480px) {
        mat-dialog-content {
          padding: 16px !important;
        }

        .update-form {
          gap: 16px;
          min-width: 250px;
        }

        mat-dialog-actions {
          padding: 12px 16px 16px 16px !important;

          ::ng-deep .mat-mdc-button {
            height: 44px;
            font-size: 14px;
            padding: 0 16px;
          }
        }
      }

      mat-dialog-actions {
        padding: 16px 24px 24px 24px !important;

        ::ng-deep .mat-mdc-button {
          height: 48px;
          font-size: 16px;
          font-weight: 600;
          border-radius: 12px;
          text-transform: none;
          letter-spacing: 0.25px;
          transition: all 0.3s ease;
          padding: 0 24px;
        }

        ::ng-deep .mat-mdc-text-button {
          background-color: transparent !important;
          color: var(--text-secondary, #666666) !important;
          border: none !important;

          &:hover:not(:disabled) {
            background-color: var(
              --surface-color,
              rgba(0, 0, 0, 0.04)
            ) !important;
          }
        }

        /* General (light mode default) disabled button styling */
        ::ng-deep .mat-mdc-raised-button:disabled {
          background-color: #f5f5f5 !important;
          color: #999999 !important;
          border: 1px solid #e0e0e0 !important;
          opacity: 1 !important;
          box-shadow: none !important;
        }

        ::ng-deep .mat-mdc-raised-button:not(:disabled) {
          background-color: var(--card-background, #ffffff) !important;
          color: var(--text-primary, #333333) !important;
          border: 1px solid var(--border-color, #dadce0) !important;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;

          &:hover:not(:disabled) {
            background-color: var(--surface-color, #f8f9fa) !important;
            border-color: var(--border-color, #c6c6c6) !important;
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15) !important;
          }

          &:active {
            transform: translateY(0);
          }
        }
      }

      /* System dark mode */
      @media (prefers-color-scheme: dark) {
        ::ng-deep .mat-mdc-dialog-surface {
          background-color: var(--card-background, #2d3748) !important;
          color: var(--text-primary, #ffffff) !important;
          border: 1px solid var(--border-color, #4a5568);
          box-shadow: 0 12px 45px rgba(0, 0, 0, 0.4),
            0 6px 25px rgba(0, 0, 0, 0.25), 0 3px 12px rgba(0, 0, 0, 0.15);
        }

        ::ng-deep .mat-mdc-dialog-title {
          color: var(--text-primary, #ffffff) !important;
        }

        ::ng-deep .mat-mdc-text-button {
          color: var(--text-secondary, #a0a0a0) !important;

          &:hover:not(:disabled) {
            background-color: var(
              --surface-color,
              rgba(255, 255, 255, 0.08)
            ) !important;
          }
        }

        ::ng-deep .mat-mdc-raised-button:not(:disabled) {
          background-color: var(--card-background, #2d3748) !important;
          color: var(--text-primary, #ffffff) !important;
          border: 1px solid var(--border-color, #4a5568) !important;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;

          &:hover:not(:disabled) {
            background-color: var(--surface-color, #374151) !important;
            border-color: var(--border-color, #4a5568) !important;
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15) !important;
          }

          &:active {
            transform: translateY(0);
          }
        }

        /* Dark mode disabled button styling */
        ::ng-deep .mat-mdc-raised-button:disabled {
          background-color: #404040 !important;
          color: #aaaaaa !important;
          border: 1px solid #666666 !important;
          opacity: 1 !important;
          box-shadow: none !important;
        }

        .full-width {
          input {
            color: #ffffff !important;
          }

          input::placeholder {
            color: #a0a0a0 !important;
            opacity: 0.7;
          }

          .mat-mdc-form-field-infix input {
            color: #ffffff !important;
          }

          .mat-mdc-form-field-label {
            color: #c0c0c0 !important;
          }

          .mat-mdc-text-field-wrapper {
            color: #ffffff !important;
          }

          .mat-mdc-floating-label {
            color: #c0c0c0 !important;
          }

          .mat-mdc-floating-label.mdc-floating-label--float-above {
            color: #42a5f5 !important;
          }

          ::ng-deep .mat-icon {
            color: #c0c0c0 !important;
          }

          ::ng-deep .success-icon {
            color: #4caf50 !important;
          }
        }
      }

      /* App dark theme override */
      :host-context(body.dark-theme) {
        ::ng-deep .mat-mdc-dialog-surface {
          background-color: var(--card-background) !important;
          color: var(--text-primary) !important;
          border: 1px solid var(--border-color);
          box-shadow: 0 12px 45px rgba(0, 0, 0, 0.4),
            0 6px 25px rgba(0, 0, 0, 0.25), 0 3px 12px rgba(0, 0, 0, 0.15);
        }

        .full-width {
          input {
            color: #ffffff !important;
          }

          input::placeholder {
            color: #a0a0a0 !important;
            opacity: 0.7;
          }

          .mat-mdc-form-field-infix input {
            color: #ffffff !important;
          }

          .mat-mdc-form-field-label {
            color: #c0c0c0 !important;
          }

          .mat-mdc-text-field-wrapper {
            color: #ffffff !important;
          }

          .mat-mdc-floating-label {
            color: #c0c0c0 !important;
          }

          .mat-mdc-floating-label.mdc-floating-label--float-above {
            color: #42a5f5 !important;
          }

          ::ng-deep .mat-mdc-form-field-subscript-wrapper {
            color: #c0c0c0 !important;
          }

          ::ng-deep .mat-icon {
            color: #c0c0c0 !important;
          }

          ::ng-deep .success-icon {
            color: #4caf50 !important;
          }
        }

        ::ng-deep .mat-mdc-raised-button:not(:disabled) {
          background-color: var(--card-background, #2d3748) !important;
          color: var(--text-primary, #ffffff) !important;
          border: 1px solid var(--border-color, #4a5568) !important;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;

          &:hover:not(:disabled) {
            background-color: var(--surface-color, #374151) !important;
            border-color: var(--border-color, #4a5568) !important;
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15) !important;
          }

          &:active {
            transform: translateY(0);
          }
        }

        /* Dark mode disabled button styling for app theme */
        ::ng-deep .mat-mdc-raised-button:disabled {
          background-color: #404040 !important;
          color: #aaaaaa !important;
          border: 1px solid #666666 !important;
          opacity: 1 !important;
          box-shadow: none !important;
        }
      }

      /* Force light mode text colors - highest priority */
      :host ::ng-deep .full-width input,
      :host ::ng-deep .full-width .mat-mdc-form-field-infix input {
        color: #333333 !important;
      }

      @media (prefers-color-scheme: light) {
        :host ::ng-deep .full-width input,
        :host ::ng-deep .full-width .mat-mdc-form-field-infix input {
          color: #333333 !important;
        }
      }

      /* Override only in dark mode */
      @media (prefers-color-scheme: dark) {
        :host ::ng-deep .full-width input,
        :host ::ng-deep .full-width .mat-mdc-form-field-infix input {
          color: #ffffff !important;
        }
      }

      :host-context(body.dark-theme) ::ng-deep .full-width input,
      :host-context(body.dark-theme)
        ::ng-deep
        .full-width
        .mat-mdc-form-field-infix
        input {
        color: #ffffff !important;
      }

      /* General disabled button styling override */
      :host ::ng-deep .mat-mdc-raised-button:disabled {
        background-color: #f5f5f5 !important;
        color: #999999 !important;
        border: 1px solid #e0e0e0 !important;
        opacity: 1 !important;
        box-shadow: none !important;
      }

      /* Success icon color override for all themes */
      :host ::ng-deep .success-icon {
        color: #4caf50 !important;
      }

      :host-context(body.dark-theme) ::ng-deep .success-icon {
        color: #4caf50 !important;
      }

      @media (prefers-color-scheme: dark) {
        :host ::ng-deep .success-icon {
          color: #4caf50 !important;
        }

        /* System dark mode disabled button styling */
        :host ::ng-deep .mat-mdc-raised-button:disabled {
          background-color: #404040 !important;
          color: #aaaaaa !important;
          border: 1px solid #666666 !important;
          opacity: 1 !important;
          box-shadow: none !important;
        }
      }
    `,
  ],
})
export class UpdateAccountDialog {
  private dialogRef = inject(MatDialogRef<UpdateAccountDialog>);
  private data = inject(MAT_DIALOG_DATA);
  private authService = inject(AuthService);
  private messageService = inject(MessageService);

  hidePassword = signal(true);
  isUpdating = signal(false);
  usernameErrorMessage = signal<string>('');
  emailErrorMessage = signal<string>('');
  passwordErrorMessage = signal<string>('');

  // Store original values for comparison
  private originalValues = {
    username: this.data.user?.username || '',
    email: this.data.user?.email || '',
  };

  form = new FormGroup({
    username: new FormControl(this.data.user?.username || '', [
      Validators.required,
      Validators.minLength(3),
    ]),
    email: new FormControl(this.data.user?.email || '', [
      Validators.required,
      strictEmailValidator,
    ]),
    password: new FormControl('', [Validators.minLength(8)]),
  });

  togglePasswordVisibility(): void {
    this.hidePassword.set(!this.hidePassword());
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

  updatePasswordErrorMessage = ErrorManagerFactory.getFormErrorManager(
    this.form.get('password')!,
    this.passwordErrorMessage.set,
    {
      minlength: ErrorManagerFactory.MSG_AT_LEAST_8_CHARS,
    }
  );

  // Check if any form field has been modified
  hasFormChanges(): boolean {
    const currentValues = this.form.value;

    // Check if username or email changed (with null/undefined safety)
    const usernameChanged =
      (currentValues.username || '') !== this.originalValues.username;
    const emailChanged =
      (currentValues.email || '') !== this.originalValues.email;

    // Check if password was provided (since it's optional and starts empty)
    const passwordProvided = !!(
      currentValues.password && currentValues.password.trim() !== ''
    );

    return usernameChanged || emailChanged || passwordProvided;
  }

  onCancel(): void {
    this.dialogRef.close();
  }

  async onSave(): Promise<void> {
    if (this.form.invalid) {
      // Update error messages for all form fields
      this.updateUsernameErrorMessage();
      this.updateEmailErrorMessage();
      this.updatePasswordErrorMessage();
      return;
    }

    this.isUpdating.set(true);

    try {
      const formData = this.form.value;
      const updateData: any = {
        username: formData.username,
        email: formData.email,
      };

      // Only include password if it's provided
      if (formData.password && formData.password.trim() !== '') {
        updateData.password = formData.password;
      }

      const success = await this.authService.updateAccount(updateData);

      if (success) {
        this.messageService.showSuccessMessage('Account updated successfully!');
        this.dialogRef.close(true);
      } else {
        this.messageService.showErrorMessage(
          'Failed to update account. Please try again.'
        );
      }
    } catch (error: any) {
      console.error('Account update error:', error);

      const errorMessage =
        error?.message || 'Failed to update account. Please try again.';
      this.messageService.showErrorMessage(errorMessage);
    } finally {
      this.isUpdating.set(false);
    }
  }
}
