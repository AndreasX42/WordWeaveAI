import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  MatDialogRef,
  MAT_DIALOG_DATA,
  MatDialogModule,
} from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatInputModule } from '@angular/material/input';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { TranslatePipe } from '../../shared/pipes/translate.pipe';
import { TranslationService } from '../../services/translation.service';
import { VocabularyWord } from '../../models/word.model';

export interface RequestWordDialogData {
  searchTerm: string;
  currentResults: VocabularyWord[];
  sourceLanguage?: string;
  targetLanguage?: string;
}

export interface RequestWordDialogResult {
  sourceWord: string;
  sourceLanguage?: string;
  targetLanguage: string;
}

@Component({
  selector: 'app-request-word-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatIconModule,
    MatTooltipModule,
    ReactiveFormsModule,
    TranslatePipe,
  ],
  templateUrl: './request-word-dialog.html',
  styleUrls: ['./request-word-dialog.scss'],
})
export class RequestWordDialogComponent {
  private translationService = inject(TranslationService);
  public dialogRef = inject(MatDialogRef<RequestWordDialogComponent>);
  public data = inject(MAT_DIALOG_DATA) as RequestWordDialogData;

  sourceLanguageControl = new FormControl<string>('', { nonNullable: true });
  targetLanguageControl = new FormControl<string>('', { nonNullable: true });
  sourceWordControl = new FormControl<string>('', { nonNullable: true });

  constructor() {
    // Initialize form controls
    this.sourceLanguageControl.setValue(this.data.sourceLanguage || '');
    this.targetLanguageControl.setValue(this.data.targetLanguage || '');
    this.sourceWordControl.setValue(this.data.searchTerm || '');
  }

  get validationErrors(): string[] {
    const errors: string[] = [];

    if (!this.sourceWordControl.value?.trim()) {
      errors.push(
        this.translationService.translate(
          'search.requestWord.validation.sourceWordRequired'
        )
      );
    }

    if (!this.targetLanguageControl.value) {
      errors.push(
        this.translationService.translate(
          'search.requestWord.validation.targetLanguageRequired'
        )
      );
    }

    return errors;
  }

  get existingResults(): VocabularyWord[] {
    if (
      !this.targetLanguageControl.value ||
      !this.sourceWordControl.value?.trim()
    )
      return [];

    const sourceWord = this.sourceWordControl.value.trim().toLowerCase();
    return this.data.currentResults.filter(
      (result) =>
        result.source_word.toLowerCase() === sourceWord &&
        result.target_language === this.targetLanguageControl.value
    );
  }

  isFormValid(): boolean {
    return (
      this.validationErrors.length === 0 && this.existingResults.length === 0
    );
  }

  getLanguageName(code: string): string {
    const language = this.translationService.languages.find(
      (lang) => lang.code === code
    );
    return language?.name || code;
  }

  getLanguageFlag(code: string): string {
    const language = this.translationService.languages.find(
      (lang) => lang.code === code
    );
    return language?.flag || '🏳️';
  }

  onCancel(): void {
    this.dialogRef.close();
  }

  onSubmit(): void {
    if (!this.isFormValid()) return;

    const result: RequestWordDialogResult = {
      sourceWord: this.sourceWordControl.value.trim(),
      sourceLanguage: this.sourceLanguageControl.value || undefined,
      targetLanguage: this.targetLanguageControl.value,
    };

    this.dialogRef.close(result);
  }
}
