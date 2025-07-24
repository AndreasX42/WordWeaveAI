import { Component, EventEmitter, Input, Output } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { CommonModule } from '@angular/common';
import { TranslatePipe } from '@/shared/pipes/translate.pipe';
import { ValidationErrorInfo } from '@/models/error.model';

export interface Suggestion {
  word: string;
  language: string;
}

@Component({
  selector: 'app-validation-error-state',
  templateUrl: './validation-error-state.html',
  styleUrls: ['./validation-error-state.scss'],
  standalone: true,
  imports: [MatIconModule, MatButtonModule, CommonModule, TranslatePipe],
})
export class ValidationErrorStateComponent {
  @Input() validationError: ValidationErrorInfo | null = null;
  @Output() goBack = new EventEmitter<void>();
  @Output() searchSuggestion = new EventEmitter<Suggestion>();
}
