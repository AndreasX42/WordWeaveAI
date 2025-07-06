import { Component, inject } from '@angular/core';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { ThemeService } from '../../services/theme.service';
import { TranslationService } from '../../services/translation.service';
import { TranslatePipe } from '../../shared/pipes/translate.pipe';

@Component({
  selector: 'app-search',
  standalone: true,
  host: {
    style: 'display: block; height: 100%; overflow: hidden;',
  },
  template: `
    <div
      class="search-container"
      [class.dark-theme]="themeService.isDarkMode()"
    >
      <!-- Animated Background -->
      <div class="background-animation">
        <div class="wave wave-1"></div>
        <div class="wave wave-2"></div>
        <div class="wave wave-3"></div>
        <div class="gradient-overlay"></div>
      </div>

      <!-- Search Section -->
      <section class="search-section">
        <div class="search-content">
          <h1 class="search-title">
            {{ 'search.title' | translate }}
            <span class="highlight-text">{{
              'search.titleHighlight' | translate
            }}</span>
          </h1>

          <p class="search-subtitle">
            {{ 'search.subtitle' | translate }}
          </p>

          <div class="search-box">
            <div class="language-selectors">
              <mat-form-field appearance="outline" class="language-select">
                <mat-label>{{ 'search.sourceLanguage' | translate }}</mat-label>
                <mat-select
                  [(ngModel)]="sourceLanguage"
                  (ngModelChange)="onLanguageChange()"
                >
                  <mat-option value="">{{
                    'search.selectLanguage' | translate
                  }}</mat-option>
                  <mat-option value="en" [disabled]="targetLanguage === 'en'"
                    >English</mat-option
                  >
                  <mat-option value="es" [disabled]="targetLanguage === 'es'"
                    >Spanish</mat-option
                  >
                  <mat-option value="de" [disabled]="targetLanguage === 'de'"
                    >German</mat-option
                  >
                </mat-select>
              </mat-form-field>

              <button
                mat-icon-button
                class="swap-button"
                (click)="swapLanguages()"
                [disabled]="!sourceLanguage && !targetLanguage"
              >
                <mat-icon>swap_horiz</mat-icon>
              </button>

              <mat-form-field appearance="outline" class="language-select">
                <mat-label>{{ 'search.targetLanguage' | translate }}</mat-label>
                <mat-select
                  [(ngModel)]="targetLanguage"
                  (ngModelChange)="onLanguageChange()"
                >
                  <mat-option value="">{{
                    'search.selectLanguage' | translate
                  }}</mat-option>
                  <mat-option value="en" [disabled]="sourceLanguage === 'en'"
                    >English</mat-option
                  >
                  <mat-option value="es" [disabled]="sourceLanguage === 'es'"
                    >Spanish</mat-option
                  >
                  <mat-option value="de" [disabled]="sourceLanguage === 'de'"
                    >German</mat-option
                  >
                </mat-select>
              </mat-form-field>
            </div>

            <mat-form-field appearance="outline" class="search-input">
              <mat-label>{{ 'search.inputPlaceholder' | translate }}</mat-label>
              <input
                matInput
                [(ngModel)]="searchTerm"
                (keyup.enter)="search()"
              />
              <button
                *ngIf="searchTerm"
                matSuffix
                mat-icon-button
                aria-label="Clear"
                (click)="searchTerm = ''"
              >
                <mat-icon>close</mat-icon>
              </button>
            </mat-form-field>

            <button
              mat-flat-button
              color="primary"
              class="search-button"
              (click)="search()"
              [disabled]="!searchTerm || !sourceLanguage || !targetLanguage"
            >
              <mat-icon>search</mat-icon>
              {{ 'search.button' | translate }}
            </button>
          </div>
        </div>
      </section>
    </div>
  `,
  styles: [
    `
      .search-container {
        position: relative;
        overflow: hidden;
        height: calc(100vh - 64px);
        box-sizing: border-box;
      }

      /* Animated Background */
      .background-animation {
        position: absolute; /* Changed from fixed */
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        z-index: -2;
        overflow: hidden;
        pointer-events: none;
      }

      .wave {
        position: absolute;
        width: 200%;
        height: 200%;
        background: linear-gradient(
          45deg,
          var(--primary-color, #1565c0) 0%,
          var(--primary-light, #42a5f5) 50%,
          var(--accent-color, #ff4081) 100%
        );
        opacity: 0.08;
        animation: wave-animation 45s ease-in-out infinite;
      }

      .wave-1 {
        animation-delay: 0s;
        animation-duration: 45s;
      }

      .wave-2 {
        animation-delay: -15s;
        animation-duration: 60s;
        opacity: 0.06;
      }

      .wave-3 {
        animation-delay: -30s;
        animation-duration: 75s;
        opacity: 0.04;
      }

      @keyframes wave-animation {
        0% {
          transform: translateX(-50%) translateY(-50%) rotate(0deg) scale(1);
          border-radius: 60% 40% 70% 30%;
        }
        50% {
          transform: translateX(-55%) translateY(-45%) rotate(180deg)
            scale(0.95);
          border-radius: 60% 40% 30% 70%;
        }
        100% {
          transform: translateX(-50%) translateY(-50%) rotate(360deg) scale(1);
          border-radius: 60% 40% 70% 30%;
        }
      }

      .gradient-overlay {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(
          135deg,
          rgba(21, 101, 192, 0.03) 0%,
          rgba(66, 165, 245, 0.02) 50%,
          rgba(255, 64, 129, 0.03) 100%
        );
        z-index: -1;
      }

      /* Search Section */
      .search-section {
        display: flex;
        justify-content: center;
        align-items: flex-start;
        height: 100%; /* Changed from min-height */
        padding: 2rem 2rem;
        overflow: hidden;
        box-sizing: border-box;
      }

      .search-content {
        width: 100%;
        max-width: 800px;
        text-align: center;
        z-index: 1;
        margin-top: 1rem;
      }

      .search-title {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.75rem;
        color: var(--text-primary);
      }

      .highlight-text {
        background: linear-gradient(
          135deg,
          var(--primary-color, #1565c0) 0%,
          var(--accent-color, #ff4081) 100%
        );
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
      }

      .search-subtitle {
        font-size: 1.1rem;
        color: var(--text-secondary);
        margin-bottom: 2rem;
        max-width: 600px;
        margin-left: auto;
        margin-right: auto;
      }

      .search-box {
        background: var(--card-background, white);
        border-radius: 24px;
        padding: 2rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        border: 1px solid var(--border-color, rgba(0, 0, 0, 0.12));
      }

      .language-selectors {
        display: flex;
        gap: 1rem;
        align-items: center;
        margin-bottom: 1.5rem;
      }

      .language-select {
        flex: 1;
      }

      .swap-button {
        margin-top: -1rem;
      }

      .swap-button:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }

      .search-input {
        width: 100%;
        margin-bottom: 1rem;
      }

      .search-button {
        width: 100%;
        padding: 1.25rem !important;
        font-size: 1.1rem !important;
        border-radius: 12px !important;
        background: linear-gradient(
          135deg,
          var(--primary-color, #1565c0) 0%,
          var(--primary-dark, #0d47a1) 100%
        ) !important;
        transition: all 0.3s ease !important;
      }

      .search-button:disabled {
        background: linear-gradient(
          135deg,
          rgba(158, 158, 158, 0.8) 0%,
          rgba(117, 117, 117, 0.8) 100%
        ) !important;
        opacity: 0.7;
        cursor: not-allowed;
      }

      .search-button:not(:disabled) {
        box-shadow: 0 4px 20px rgba(var(--primary-color-rgb, 21, 101, 192), 0.3) !important;
      }

      .search-button:not(:disabled):hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(var(--primary-color-rgb, 21, 101, 192), 0.4) !important;
      }

      /* Dark theme adjustments */
      .dark-theme .wave {
        background: linear-gradient(
          45deg,
          rgba(13, 71, 161, 0.6) 0%,
          rgba(66, 165, 245, 0.4) 50%,
          rgba(255, 64, 129, 0.3) 100%
        );
        opacity: 0.12;
      }

      .dark-theme .gradient-overlay {
        background: linear-gradient(
          135deg,
          rgba(13, 71, 161, 0.08) 0%,
          rgba(66, 165, 245, 0.06) 50%,
          rgba(255, 64, 129, 0.08) 100%
        );
      }

      .dark-theme .search-box {
        background: var(--card-background);
        border-color: var(--border-color);
      }

      /* Dark theme form field styles */
      .dark-theme {
        ::ng-deep {
          .mat-mdc-form-field {
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

            /* Ensure label is visible when not floating */
            .mdc-floating-label {
              color: var(--text-secondary) !important;
            }

            /* Label when field is focused */
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

          .mat-mdc-select-panel {
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
        }
      }

      /* Responsive adjustments */
      @media (max-width: 768px) {
        .search-section {
          padding: 1.5rem 1rem;
        }

        .search-content {
          margin-top: 0.5rem;
        }

        .search-title {
          font-size: 2rem;
        }

        .search-box {
          padding: 1.5rem;
        }

        .language-selectors {
          flex-direction: column;
          gap: 0.5rem;
        }

        .swap-button {
          transform: rotate(90deg);
          margin: 0;
        }
      }

      @media (max-width: 480px) {
        .search-title {
          font-size: 1.75rem;
        }

        .search-subtitle {
          font-size: 1rem;
        }

        .search-box {
          padding: 1rem;
        }
      }
    `,
  ],
  imports: [
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    FormsModule,
    CommonModule,
    TranslatePipe,
  ],
})
export class Search {
  themeService = inject(ThemeService);
  translationService = inject(TranslationService);
  router = inject(Router);

  searchTerm = '';
  sourceLanguage = '';
  targetLanguage = '';

  private readonly STORAGE_KEY_SOURCE = 'source_language';
  private readonly STORAGE_KEY_TARGET = 'target_language';

  constructor() {
    // Load saved language preferences from localStorage
    this.loadLanguagePreferences();
  }

  private loadLanguagePreferences() {
    const savedSourceLanguage = localStorage.getItem(this.STORAGE_KEY_SOURCE);
    const savedTargetLanguage = localStorage.getItem(this.STORAGE_KEY_TARGET);

    if (savedSourceLanguage !== null) {
      this.sourceLanguage = savedSourceLanguage;
    }
    if (savedTargetLanguage !== null) {
      this.targetLanguage = savedTargetLanguage;
    }
  }

  private saveLanguagePreferences() {
    localStorage.setItem(this.STORAGE_KEY_SOURCE, this.sourceLanguage);
    localStorage.setItem(this.STORAGE_KEY_TARGET, this.targetLanguage);
  }

  onLanguageChange() {
    this.saveLanguagePreferences();
  }

  swapLanguages() {
    [this.sourceLanguage, this.targetLanguage] = [
      this.targetLanguage,
      this.sourceLanguage,
    ];
    this.saveLanguagePreferences();
  }

  search() {
    if (this.searchTerm && this.sourceLanguage && this.targetLanguage) {
      // Navigate to the word card page
      this.router.navigate([
        '/words',
        this.sourceLanguage,
        this.targetLanguage,
        this.searchTerm.toLowerCase().trim(),
      ]);
    }
  }
}
