import { AbstractControl } from '@angular/forms';

export class ErrorManagerFactory {
  static MSG_IS_REQUIRED = 'This field is required';
  static MSG_AT_LEAST_3_CHARS = 'Must be at least 3 characters';
  static MSG_AT_LEAST_6_CHARS = 'Must be at least 6 characters';
  static MSG_AT_LEAST_8_CHARS = 'Must be at least 8 characters';
  static MSG_INVALID_EMAIL = 'Please enter a valid email address';
  static MSG_VALID_EMAIL = 'Please enter a valid email address';

  static getFormErrorManager(
    control: AbstractControl,
    setErrorMessage: (message: string) => void,
    errorMessages: Record<string, string>
  ) {
    return () => {
      if (control.valid || control.untouched) {
        setErrorMessage('');
        return;
      }

      const errors = control.errors;
      if (!errors) {
        setErrorMessage('');
        return;
      }

      const firstErrorKey = Object.keys(errors)[0];
      const errorMessage = errorMessages[firstErrorKey] || 'Invalid input';
      setErrorMessage(errorMessage);
    };
  }
}
