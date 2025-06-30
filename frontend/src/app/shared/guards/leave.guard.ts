import { CanDeactivateFn } from '@angular/router';
import { FormGroup } from '@angular/forms';

interface CanDeactivateEditComponent {
  form?: FormGroup;
}

interface CanDeactivateSolveComponent {
  isCompleted(): boolean;
}

export const canLeaveEditPage: CanDeactivateFn<CanDeactivateEditComponent> = (
  component
) => {
  if (component.form && component.form.touched && component.form.invalid) {
    return window.confirm('Do you really want to leave?');
  }
  return true;
};

export const canLeaveSolvePage: CanDeactivateFn<CanDeactivateSolveComponent> = (
  component
) => {
  if (component.isCompleted()) {
    return true;
  }

  return window.confirm(
    'Do you really want to leave? Any progress will not be saved.'
  );
};
