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
  template: `
    <h2 mat-dialog-title>
      <mat-icon>add_circle</mat-icon>
      {{ 'search.requestWord.dialog.title' | translate }}
    </h2>

    <mat-dialog-content>
      <div class="form-section">
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>{{
            'search.requestWord.dialog.sourceWordPlaceholder' | translate
          }}</mat-label>
          <input
            matInput
            [formControl]="sourceWordControl"
            [matTooltip]="
              'search.requestWord.dialog.sourceWordHint' | translate
            "
            matTooltipPosition="below"
          />
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>{{
            'search.requestWord.dialog.sourceLanguage' | translate
          }}</mat-label>
          <mat-select [formControl]="sourceLanguageControl">
            <mat-option value="">{{
              'search.requestWord.dialog.autoDetect' | translate
            }}</mat-option>
            <mat-option value="en">English</mat-option>
            <mat-option value="es">Spanish</mat-option>
            <mat-option value="de">German</mat-option>
          </mat-select>
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>{{
            'search.requestWord.dialog.targetLanguage' | translate
          }}</mat-label>
          <mat-select [formControl]="targetLanguageControl">
            <mat-option value="en">English</mat-option>
            <mat-option value="es">Spanish</mat-option>
            <mat-option value="de">German</mat-option>
          </mat-select>
        </mat-form-field>
      </div>

      <!-- Validation Messages -->
      <div class="validation-section" *ngIf="validationErrors.length > 0">
        <div class="validation-error" *ngFor="let error of validationErrors">
          <mat-icon>error_outline</mat-icon>
          <span>{{ error }}</span>
        </div>
      </div>

      <!-- Existing Results Warning -->
      <div class="existing-results" *ngIf="existingResults.length > 0">
        <mat-icon>info</mat-icon>
        <div class="warning-content">
          <p class="warning-title">
            {{ 'search.requestWord.dialog.existingResults' | translate }}
          </p>
          <div class="existing-items">
            <div class="existing-item" *ngFor="let result of existingResults">
              <span class="flag">{{
                getLanguageFlag(result.source_language)
              }}</span>
              <span class="word">{{ result.source_word }}</span>
              <mat-icon class="arrow">arrow_forward</mat-icon>
              <span class="flag">{{
                getLanguageFlag(result.target_language)
              }}</span>
              <span class="word">{{ result.target_word }}</span>
            </div>
          </div>
        </div>
      </div>
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button mat-button (click)="onCancel()">
        {{ 'common.cancel' | translate }}
      </button>
      <button
        mat-raised-button
        color="primary"
        (click)="onSubmit()"
        [disabled]="!isFormValid()"
      >
        {{ 'search.requestWord.dialog.submit' | translate }}
      </button>
    </mat-dialog-actions>
  `,
  styles: [
    `
      /* Clean form styling - like auth forms */
      .form-section {
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
      }

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
        display: flex;
        align-items: center;
        gap: 8px;
      }

      ::ng-deep .mat-mdc-dialog-title mat-icon {
        font-size: 24px;
        width: 24px;
        height: 24px;
        color: #1976d2;
      }

      .form-section {
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
      }

      /* Language selector styling to match search container */
      .language-select {
        flex: 1;
      }

      .validation-section {
        margin-bottom: 16px;
      }

      .validation-error {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        background: rgba(244, 67, 54, 0.1);
        border-radius: 4px;
        margin-bottom: 8px;

        mat-icon {
          font-size: 16px;
          width: 16px;
          height: 16px;
          color: #f44336;
        }

        span {
          font-size: 14px;
          color: #d32f2f;
        }
      }

      .existing-results {
        display: flex;
        gap: 12px;
        padding: 12px;
        background: rgba(255, 193, 7, 0.1);
        border-radius: 6px;
        border: 1px solid rgba(255, 193, 7, 0.3);

        mat-icon {
          font-size: 20px;
          width: 20px;
          height: 20px;
          color: #f57c00;
          flex-shrink: 0;
          margin-top: 2px;
        }

        .warning-content {
          flex: 1;
        }

        .warning-title {
          font-weight: 500;
          color: #f57c00;
          margin: 0 0 8px 0;
          font-size: 14px;
        }

        .existing-items {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .existing-item {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 13px;
          color: #666;

          .flag {
            font-size: 14px;
          }

          .word {
            font-weight: 500;
          }

          .arrow {
            font-size: 14px;
            width: 14px;
            height: 14px;
            color: #999;
          }
        }
      }

      mat-dialog-content {
        padding: 24px 24px 16px 24px !important;
      }

      mat-dialog-actions {
        padding: 8px 24px 24px 24px !important;

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

        ::ng-deep .mat-mdc-raised-button:disabled {
          background-color: #f5f5f5 !important;
          color: #999999 !important;
          border: 1px solid #e0e0e0 !important;
          opacity: 1 !important;
          box-shadow: none !important;
        }
      }

      /* Light mode - ensure it overrides all dark mode styles */
      @media (prefers-color-scheme: light),
        (prefers-color-scheme: no-preference) {
        .full-width {
          input {
            color: #333333 !important;
            -webkit-text-fill-color: #333333 !important;
          }

          input::placeholder {
            color: #666666 !important;
            opacity: 0.7;
          }

          .mat-mdc-form-field-infix input {
            color: #333333 !important;
            -webkit-text-fill-color: #333333 !important;
          }

          .mat-mdc-input-element {
            color: #333333 !important;
            -webkit-text-fill-color: #333333 !important;
          }

          .mat-mdc-form-field-label {
            color: #666666 !important;
          }

          .mat-mdc-text-field-wrapper {
            color: #333333 !important;
          }

          .mat-mdc-floating-label {
            color: #666666 !important;
          }

          .mat-mdc-floating-label.mdc-floating-label--float-above {
            color: #1976d2 !important;
          }
        }

        ::ng-deep .full-width input {
          color: #333333 !important;
          -webkit-text-fill-color: #333333 !important;
        }

        ::ng-deep .full-width input::placeholder {
          color: #666666 !important;
          opacity: 0.7;
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

        ::ng-deep .full-width .mat-mdc-input-element {
          color: #333333 !important;
          -webkit-text-fill-color: #333333 !important;
        }

        ::ng-deep .full-width .mat-mdc-form-field-infix input {
          color: #333333 !important;
          -webkit-text-fill-color: #333333 !important;
        }

        ::ng-deep .full-width .mat-mdc-text-field-wrapper {
          color: #333333 !important;
        }
      }

      /* Default light mode when no theme preference is set */
      :host:not(.dark-theme):not(:host-context(body.dark-theme)) {
        .full-width {
          input {
            color: #333333 !important;
            -webkit-text-fill-color: #333333 !important;
          }

          .mat-mdc-input-element {
            color: #333333 !important;
            -webkit-text-fill-color: #333333 !important;
          }

          .mat-mdc-form-field-infix input {
            color: #333333 !important;
            -webkit-text-fill-color: #333333 !important;
          }
        }
      }

      /* DEFAULT: Light mode text colors */
      .full-width {
        input {
          color: #333333 !important;
          -webkit-text-fill-color: #333333 !important;
        }

        .mat-mdc-input-element {
          color: #333333 !important;
          -webkit-text-fill-color: #333333 !important;
        }

        .mat-mdc-form-field-infix input {
          color: #333333 !important;
          -webkit-text-fill-color: #333333 !important;
        }
      }

      /* App dark theme override - clean styling */
      :host-context(body.dark-theme) {
        .simple-input {
          background: var(--card-background);
          border-color: var(--border-color);
          color: var(--text-primary);
        }

        .input-label {
          color: var(--text-primary);
        }
        ::ng-deep .mat-mdc-dialog-surface {
          background-color: var(--card-background) !important;
          color: var(--text-primary) !important;
          border: 1px solid var(--border-color);
          box-shadow: 0 12px 45px rgba(0, 0, 0, 0.4),
            0 6px 25px rgba(0, 0, 0, 0.25), 0 3px 12px rgba(0, 0, 0, 0.15);
        }

        /* Dark theme form fields - exact copy from search container */
        ::ng-deep .mat-mdc-form-field {
          .mat-mdc-text-field-wrapper {
            background-color: rgba(255, 255, 255, 0.05) !important;
          }

          .mat-mdc-form-field-flex {
            color: var(--text-primary) !important;
          }

          .mat-mdc-input-element {
            color: var(--text-primary) !important;
            caret-color: var(--text-primary) !important;
          }

          .mat-mdc-form-field-label {
            color: var(--text-secondary) !important;
          }

          .mat-mdc-form-field-label.mdc-floating-label--float-above {
            color: var(--primary-light) !important;
          }

          .mdc-floating-label {
            color: var(--text-secondary) !important;
          }

          &.mat-focused .mdc-floating-label {
            color: var(--primary-light) !important;
          }

          .mat-mdc-select-value {
            color: var(--text-primary) !important;
          }

          .mat-mdc-select-arrow {
            color: var(--text-secondary) !important;
          }

          .mat-mdc-form-field-subscript-wrapper {
            color: var(--text-secondary) !important;
          }

          .mat-mdc-form-field-outline {
            color: var(--border-color) !important;
          }

          &.mat-focused {
            .mat-mdc-form-field-outline {
              color: var(--primary-light) !important;
            }
          }
        }

        ::ng-deep .mat-mdc-select-panel {
          background: var(--card-background) !important;

          .mat-mdc-option {
            color: var(--text-primary) !important;

            &:hover:not(.mdc-list-item--disabled) {
              background: rgba(255, 255, 255, 0.08) !important;
            }

            &.mat-mdc-option-active {
              background: rgba(255, 255, 255, 0.12) !important;
            }

            &.mdc-list-item--disabled {
              opacity: 0.5 !important;
              cursor: not-allowed !important;
            }
          }
        }

        .full-width {
          input {
            color: var(--text-primary) !important;
            -webkit-text-fill-color: var(--text-primary) !important;
          }

          input::placeholder {
            color: var(--text-secondary, #a0a0a0) !important;
            opacity: 0.7;
          }

          .mat-mdc-form-field-infix input {
            color: var(--text-primary) !important;
            -webkit-text-fill-color: var(--text-primary) !important;
          }

          .mat-mdc-input-element {
            color: var(--text-primary) !important;
            -webkit-text-fill-color: var(--text-primary) !important;
          }

          .mat-mdc-form-field-label {
            color: var(--text-secondary, #c0c0c0) !important;
          }

          .mat-mdc-text-field-wrapper {
            color: var(--text-primary) !important;
          }

          .mat-mdc-floating-label {
            color: var(--text-secondary, #c0c0c0) !important;
          }

          .mat-mdc-floating-label.mdc-floating-label--float-above {
            color: var(--primary-light, #42a5f5) !important;
          }

          ::ng-deep .mat-mdc-form-field-subscript-wrapper {
            color: var(--text-secondary, #c0c0c0) !important;
          }

          ::ng-deep .mat-icon {
            color: var(--text-secondary, #c0c0c0) !important;
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

        ::ng-deep .mat-mdc-raised-button:disabled {
          background-color: #404040 !important;
          color: #aaaaaa !important;
          border: 1px solid #666666 !important;
          opacity: 1 !important;
          box-shadow: none !important;
        }

        .validation-error {
          background: rgba(244, 67, 54, 0.15);

          span {
            color: #ff8a80;
          }
        }

        .existing-results {
          background: rgba(255, 193, 7, 0.15);
          border-color: rgba(255, 193, 7, 0.4);

          .warning-title {
            color: #ffb74d;
          }

          .existing-item {
            color: #b0b0b0;
          }
        }
      }

      /* Force light mode text colors with highest specificity - override all other styles */
      :host ::ng-deep .full-width input {
        color: #333333 !important;
        -webkit-text-fill-color: #333333 !important;
      }

      :host ::ng-deep .full-width .mat-mdc-input-element {
        color: #333333 !important;
        -webkit-text-fill-color: #333333 !important;
      }

      :host ::ng-deep .full-width .mat-mdc-form-field-infix input {
        color: #333333 !important;
        -webkit-text-fill-color: #333333 !important;
      }

      /* Only apply white text in actual dark mode contexts */
      @media (prefers-color-scheme: dark) {
        :host ::ng-deep .full-width input {
          color: #ffffff !important;
          -webkit-text-fill-color: #ffffff !important;
        }

        :host ::ng-deep .full-width .mat-mdc-input-element {
          color: #ffffff !important;
          -webkit-text-fill-color: #ffffff !important;
        }

        :host ::ng-deep .full-width .mat-mdc-form-field-infix input {
          color: #ffffff !important;
          -webkit-text-fill-color: #ffffff !important;
        }
      }

      :host-context(body.dark-theme) ::ng-deep .full-width input {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
      }

      :host-context(body.dark-theme)
        ::ng-deep
        .full-width
        .mat-mdc-input-element {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
      }

      :host-context(body.dark-theme)
        ::ng-deep
        .full-width
        .mat-mdc-form-field-infix
        input {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
      }

      /* ULTIMATE OVERRIDE: Force correct text colors with maximum specificity */
      ::ng-deep
        app-request-word-dialog
        .mat-mdc-form-field
        .mat-mdc-input-element {
        color: #333333 !important;
        -webkit-text-fill-color: #333333 !important;
      }

      ::ng-deep
        app-request-word-dialog
        .mat-mdc-form-field
        .mat-mdc-form-field-infix
        input {
        color: #333333 !important;
        -webkit-text-fill-color: #333333 !important;
      }

      /* Only white text in dark contexts */
      @media (prefers-color-scheme: dark) {
        ::ng-deep
          app-request-word-dialog
          .mat-mdc-form-field
          .mat-mdc-input-element {
          color: #ffffff !important;
          -webkit-text-fill-color: #ffffff !important;
        }

        ::ng-deep
          app-request-word-dialog
          .mat-mdc-form-field
          .mat-mdc-form-field-infix
          input {
          color: #ffffff !important;
          -webkit-text-fill-color: #ffffff !important;
        }
      }

      :host-context(body.dark-theme)
        ::ng-deep
        .mat-mdc-form-field
        .mat-mdc-input-element {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
      }

      :host-context(body.dark-theme)
        ::ng-deep
        .mat-mdc-form-field
        .mat-mdc-form-field-infix
        input {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
      }

      @media (max-width: 480px) {
        mat-dialog-content {
          padding: 16px 16px 12px 16px !important;
        }

        .form-section {
          gap: 16px;
          min-width: 250px;
        }

        mat-dialog-actions {
          padding: 8px 16px 16px 16px !important;

          ::ng-deep .mat-mdc-button {
            height: 44px;
            font-size: 14px;
            padding: 0 16px;
          }
        }

        .existing-results {
          padding: 10px;

          .warning-title {
            font-size: 13px;
          }

          .existing-item {
            font-size: 12px;
          }
        }
      }
    `,
  ],
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
