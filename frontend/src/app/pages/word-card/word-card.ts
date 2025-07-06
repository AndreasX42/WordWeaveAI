import { Component, inject, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTabsModule } from '@angular/material/tabs';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ThemeService } from '../../services/theme.service';
import { TranslationService } from '../../services/translation.service';
import { TranslatePipe } from '../../shared/pipes/translate.pipe';
import { WordService } from '../../services/word.service';
import { VocabularyWord } from '../../models/word.model';

@Component({
  selector: 'app-word-card',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatTabsModule,
    MatChipsModule,
    MatDividerModule,
    MatProgressSpinnerModule,
    TranslatePipe,
  ],
  template: `
    <div
      class="word-card-container"
      [class.dark-theme]="themeService.isDarkMode()"
    >
      <div class="content-wrapper">
        <!-- Loading State -->
        <div *ngIf="loading" class="loading-container">
          <mat-spinner></mat-spinner>
          <p>{{ 'wordCard.loading' | translate }}</p>
        </div>

        <!-- Error State -->
        <div *ngIf="error && !loading" class="error-container">
          <mat-icon>error_outline</mat-icon>
          <h2>{{ 'wordCard.errorTitle' | translate }}</h2>
          <p>{{ error }}</p>
          <button mat-flat-button color="primary" (click)="goBack()">
            {{ 'common.back' | translate }}
          </button>
        </div>

        <!-- Word Card -->
        <div *ngIf="word && !loading" class="word-card">
          <!-- Header Section -->
          <div class="word-header">
            <div class="word-title-section">
              <h1 class="source-word">
                {{ word.source_word }}
              </h1>
              <h2 class="target-word">
                {{ word.target_word }}
                <button
                  mat-icon-button
                  (click)="playPronunciation()"
                  *ngIf="word.pronunciation_url"
                  class="pronunciation-button"
                >
                  <mat-icon>volume_up</mat-icon>
                </button>
              </h2>
              <div
                class="pronunciation"
                *ngIf="
                  word.target_syllables && word.target_syllables.length > 0
                "
              >
                ({{ word.target_syllables.join('-') }})
                <span *ngIf="word.target_phonetic_guide" class="phonetic-guide">
                  [{{ word.target_phonetic_guide }}]
                </span>
              </div>
            </div>
            <button mat-stroked-button class="add-to-list-button">
              <mat-icon>playlist_add</mat-icon>
              {{ 'wordCard.addToList' | translate }}
            </button>
          </div>

          <!-- Header Content Section -->
          <div class="header-content">
            <div class="content-left">
              <!-- Part of Speech Tags -->
              <div class="pos-tags">
                <div class="language-flags">
                  <span class="language-flag">{{
                    getLanguageFlag(word?.source_language)
                  }}</span>
                  <mat-icon class="arrow-icon">arrow_forward</mat-icon>
                  <span class="language-flag">{{
                    getLanguageFlag(word?.target_language)
                  }}</span>
                </div>
                <div *ngIf="word.target_part_of_speech" class="pos-tag">
                  {{ word.source_part_of_speech }}
                </div>
              </div>

              <!-- Usage Hint -->
              <div class="usage-hint">
                <mat-icon class="hint-icon">info</mat-icon>
                <span>Commonly used in legal and financial contexts.</span>
              </div>
            </div>

            <!-- Media Section -->
            <div
              class="media-section"
              *ngIf="word.media && word.media.length > 0"
            >
              <img
                [src]="word.media[0].url"
                [alt]="word.media[0].caption || word.target_word"
                class="word-image"
              />
            </div>
          </div>

          <!-- Tabs Section -->
          <mat-tab-group class="content-tabs">
            <!-- Definitions Tab -->
            <mat-tab>
              <ng-template mat-tab-label>
                <mat-icon>description</mat-icon>
                {{ 'wordCard.definition' | translate }}
              </ng-template>

              <div class="tab-content">
                <div class="definitions" *ngIf="word.source_definition">
                  <ul *ngIf="isArray(word.source_definition)">
                    <li
                      *ngFor="
                        let def of asArray(word.source_definition);
                        let i = index
                      "
                    >
                      <span class="definition-number">{{ i + 1 }}.</span>
                      <span class="definition-text">{{ def }}</span>
                    </li>
                  </ul>
                  <p
                    *ngIf="!isArray(word.source_definition)"
                    class="single-definition"
                  >
                    {{ word.source_definition }}
                  </p>
                </div>
              </div>
            </mat-tab>

            <!-- Synonyms Tab -->
            <mat-tab>
              <ng-template mat-tab-label>
                <mat-icon>compare_arrows</mat-icon>
                {{ 'wordCard.synonyms' | translate }}
              </ng-template>

              <div class="tab-content">
                <div
                  class="synonyms-list"
                  *ngIf="word.synonyms && word.synonyms.length > 0"
                >
                  <div
                    *ngFor="let synonym of word.synonyms; let i = index"
                    class="synonym-item"
                  >
                    <div class="synonym-header">
                      <span class="synonym-number">{{ i + 1 }}.</span>
                      <span class="synonym-word">{{ synonym.synonym }}</span>
                    </div>
                    <p class="synonym-explanation">{{ synonym.explanation }}</p>
                  </div>
                </div>
              </div>
            </mat-tab>

            <!-- Examples Tab -->
            <mat-tab>
              <ng-template mat-tab-label>
                <mat-icon>format_quote</mat-icon>
                {{ 'wordCard.examples' | translate }}
              </ng-template>

              <div class="tab-content">
                <div
                  class="examples-list"
                  *ngIf="word.examples && word.examples.length > 0"
                >
                  <div
                    class="example-item"
                    *ngFor="let example of word.examples"
                  >
                    <div class="example-text">
                      <p class="source-example">{{ example.original }}</p>
                      <p class="target-example">{{ example.translation }}</p>
                    </div>
                    <div class="example-context" *ngIf="example.context">
                      <mat-icon class="context-icon">lightbulb</mat-icon>
                      <span>{{ example.context }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </mat-tab>

            <!-- Conjugation Tab (if applicable) -->
            <mat-tab *ngIf="word.conjugation_table">
              <ng-template mat-tab-label>
                <mat-icon>table_chart</mat-icon>
                {{ 'wordCard.conjugation' | translate }}
              </ng-template>

              <div class="tab-content">
                <div class="conjugation-table">
                  <!-- Non-personal forms -->
                  <div
                    *ngIf="word.conjugation_table?.formas_no_personales"
                    class="tense-section"
                  >
                    <h4>
                      {{
                        'wordCard.conjugationData.nonPersonalForms' | translate
                      }}
                    </h4>
                    <table>
                      <tr>
                        <td class="pronoun">
                          {{
                            'wordCard.conjugationData.infinitive' | translate
                          }}
                        </td>
                        <td class="conjugation">
                          {{
                            word.conjugation_table.formas_no_personales
                              ?.infinitivo || ''
                          }}
                        </td>
                      </tr>
                      <tr>
                        <td class="pronoun">
                          {{
                            'wordCard.conjugationData.participle' | translate
                          }}
                        </td>
                        <td class="conjugation">
                          {{
                            word.conjugation_table.formas_no_personales
                              ?.participio || ''
                          }}
                        </td>
                      </tr>
                      <tr>
                        <td class="pronoun">
                          {{ 'wordCard.conjugationData.gerund' | translate }}
                        </td>
                        <td class="conjugation">
                          {{
                            word.conjugation_table.formas_no_personales
                              ?.gerundio || ''
                          }}
                        </td>
                      </tr>
                    </table>
                  </div>

                  <!-- Indicative mood -->
                  <div
                    *ngIf="word.conjugation_table?.indicativo"
                    class="mood-section"
                  >
                    <h3>
                      {{ 'wordCard.conjugationData.indicative' | translate }}
                    </h3>
                    <div
                      *ngFor="let tense of getIndicativeTenses()"
                      class="tense-section"
                    >
                      <h4>{{ getConjugationTenseLabel(tense) }}</h4>
                      <table>
                        <tr
                          *ngFor="
                            let pronoun of getConjugationPronouns(
                              'indicativo',
                              tense
                            )
                          "
                        >
                          <td class="pronoun">
                            {{ getPronounLabel(pronoun) }}
                          </td>
                          <td class="conjugation">
                            {{
                              word.conjugation_table!.indicativo![tense][
                                pronoun
                              ]
                            }}
                          </td>
                        </tr>
                      </table>
                    </div>
                  </div>

                  <!-- Subjunctive mood -->
                  <div
                    *ngIf="word.conjugation_table?.subjuntivo"
                    class="mood-section"
                  >
                    <h3>
                      {{ 'wordCard.conjugationData.subjunctive' | translate }}
                    </h3>
                    <div
                      *ngFor="let tense of getSubjunctiveTenses()"
                      class="tense-section"
                    >
                      <h4>{{ getConjugationTenseLabel(tense) }}</h4>
                      <table>
                        <tr
                          *ngFor="
                            let pronoun of getConjugationPronouns(
                              'subjuntivo',
                              tense
                            )
                          "
                        >
                          <td class="pronoun">
                            {{ getPronounLabel(pronoun) }}
                          </td>
                          <td class="conjugation">
                            {{
                              word.conjugation_table!.subjuntivo![tense][
                                pronoun
                              ]
                            }}
                          </td>
                        </tr>
                      </table>
                    </div>
                  </div>
                </div>
              </div>
            </mat-tab>
          </mat-tab-group>

          <!-- Metadata Footer -->
          <div class="metadata-footer">
            <span
              >{{ 'wordCard.createdBy' | translate }}:
              {{ word.created_by }}</span
            >
            <span *ngIf="word.created_at">{{
              formatDate(word.created_at)
            }}</span>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [
    `
      .word-card-container {
        padding: 2rem;
        max-width: 900px;
        margin: 0 auto;
      }

      .word-card {
        background: var(--mat-card-bg-color);
        border-radius: 12px;
        padding: 2rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        position: relative;
      }

      .word-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 2rem;
      }

      .word-title-section {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
      }

      .source-word,
      .target-word {
        display: flex;
        align-items: center;
        gap: 0.75rem;
      }

      .language-flag {
        font-size: 1.125rem;
        line-height: 1;
        filter: drop-shadow(0 1px 1px rgba(0, 0, 0, 0.1));
      }

      .source-word {
        font-size: 2.5rem;
        margin: 0;
        font-weight: 500;
        color: var(--mat-text-primary-color);
        line-height: 1.2;

        .language-flag {
          margin-top: 0.375rem;
        }
      }

      .target-word {
        font-size: 2rem;
        margin: 0;
        color: #1976d2;
        line-height: 1.2;

        .language-flag {
          margin-top: 0.25rem;
        }
      }

      .pronunciation-button {
        color: #1976d2 !important;
      }

      .pronunciation-button mat-icon {
        font-size: 1.5rem;
        width: 1.5rem;
        height: 1.5rem;
      }

      .pronunciation {
        color: var(--mat-text-secondary-color);
        font-size: 1rem;
        margin: 0;
        line-height: 1.2;
      }

      .add-to-list-button {
        position: absolute;
        top: 1rem;
        right: 1rem;
        border: 1px solid #1976d2 !important;
        color: #1976d2;
        transition: all 0.2s ease-in-out;
        padding: 0.5rem 1.25rem;
        font-weight: 500;
        height: fit-content;
        border-radius: 4px;
        background-color: transparent !important;
        z-index: 1;
      }

      .add-to-list-button:hover {
        background-color: rgba(25, 118, 210, 0.1) !important;
      }

      .add-to-list-button mat-icon {
        margin-right: 0.5rem;
      }

      .header-content {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 2rem;
        position: relative;
        margin-top: 0;
      }

      .content-left {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 1rem;
        padding-top: 0.5rem;
      }

      .pos-tags {
        display: flex;
        gap: 0.5rem;
        align-items: center;
        flex-wrap: wrap;
      }

      .language-flags {
        display: flex;
        align-items: center;
        gap: 0.375rem;
        padding: 0.25rem 0.75rem;
        background-color: rgba(25, 118, 210, 0.08);
        border-radius: 16px;
        height: 24px;
        font-weight: 500;
      }

      .language-flag {
        font-size: 1.125rem;
        line-height: 1;
        margin-top: -1px;
      }

      .arrow-icon {
        font-size: 0.9rem;
        width: 0.9rem;
        height: 0.9rem;
        opacity: 0.7;
        margin-top: 1px;
      }

      .pos-tag {
        color: #1976d2;
        font-size: 0.9rem;
        padding: 0.25rem 0.75rem;
        border-radius: 16px;
        background-color: rgba(25, 118, 210, 0.08);
        display: inline-flex;
        align-items: center;
        height: 24px;
        font-weight: 500;
        letter-spacing: 0.25px;
        white-space: nowrap;
      }

      .usage-hint {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 0.75rem;
        background-color: rgba(25, 118, 210, 0.04);
        border-radius: 6px;
        font-size: 0.9rem;
        color: rgba(0, 0, 0, 0.7);
        margin-top: 0.75rem;
        max-width: fit-content;
      }

      .hint-icon {
        font-size: 1.1rem;
        width: 1.1rem;
        height: 1.1rem;
        color: #1976d2;
        opacity: 0.8;
      }

      .media-section {
        width: 200px;
        flex-shrink: 0;
        margin-top: -3rem;
        position: relative;
        z-index: 1;
      }

      .word-image {
        width: 100%;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
      }

      /* Loading and Error States */
      .loading-container,
      .error-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 400px;
        gap: 1rem;
      }

      .error-container mat-icon {
        font-size: 48px;
        width: 48px;
        height: 48px;
        color: var(--warn-color);
      }

      /* Tabs */
      .content-tabs {
        margin-top: 2rem;

        ::ng-deep {
          .mat-mdc-tab-header {
            display: flex;
            justify-content: center;
            width: 100%;
          }

          .mat-mdc-tab-list {
            flex-grow: 0;
          }

          .mat-mdc-tab-header-pagination {
            min-width: 32px;

            &-before,
            &-after {
              padding: 0 6px;
            }

            &-chevron {
              border-width: 2px 2px 0 0;
            }
          }
        }
      }

      .tab-content {
        padding: 1.5rem 0;
      }

      .definitions {
        color: rgba(0, 0, 0, 0.87);
      }

      .definitions ul {
        list-style: none;
        padding: 0;
        margin: 0;
        display: flex;
        flex-direction: column;
        gap: 1rem;
      }

      .definitions li {
        display: flex;
        gap: 1rem;
        align-items: flex-start;
        line-height: 1.5;
        padding: 0.75rem 1rem;
        background-color: rgba(25, 118, 210, 0.02);
        border-radius: 8px;
        transition: background-color 0.2s ease;
      }

      .definitions li:hover {
        background-color: rgba(25, 118, 210, 0.04);
      }

      .definition-number {
        color: #1976d2;
        font-weight: 500;
        min-width: 1.5rem;
        opacity: 0.9;
      }

      .definition-text {
        flex: 1;
      }

      .single-definition {
        line-height: 1.5;
        padding: 0.75rem 1rem;
        margin: 0;
        background-color: rgba(25, 118, 210, 0.02);
        border-radius: 8px;
      }

      /* Synonyms List */
      .synonyms-list {
        display: flex;
        flex-direction: column;
        gap: 1.25rem;
      }

      .synonym-item {
        background-color: rgba(0, 0, 0, 0.01);
        border-radius: 8px;
        border-left: 4px solid #1976d2;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
      }

      .synonym-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 1rem;
        border-bottom: 1px solid rgba(0, 0, 0, 0.05);
        background-color: rgba(0, 0, 0, 0.005);
      }

      .synonym-number {
        color: #1976d2;
        font-weight: 500;
        opacity: 0.9;
      }

      .synonym-word {
        color: #1976d2;
        font-weight: 500;
      }

      .synonym-explanation {
        margin: 0;
        padding: 1rem;
        color: rgba(0, 0, 0, 0.7);
        line-height: 1.5;
      }

      .media-container {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
        justify-content: center;
      }

      .word-image {
        max-width: 400px;
        width: 100%;
        height: auto;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      }

      /* Examples Tab */
      .examples-list {
        display: flex;
        flex-direction: column;
        gap: 1.25rem;
      }

      .example-item {
        background-color: rgba(0, 0, 0, 0.01);
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        overflow: hidden;
      }

      .example-text {
        padding: 1rem;
        border-bottom: 1px solid rgba(0, 0, 0, 0.05);
        background-color: rgba(0, 0, 0, 0.005);
      }

      .source-example {
        margin: 0;
        font-size: 1rem;
        line-height: 1.5;
        color: rgba(0, 0, 0, 0.87);
      }

      .target-example {
        margin: 0.75rem 0 0;
        color: rgba(0, 0, 0, 0.6);
        line-height: 1.5;
        padding-left: 1rem;
        border-left: 2px solid rgba(0, 0, 0, 0.1);
      }

      .example-context {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.75rem 1rem;
        background-color: rgba(25, 118, 210, 0.04);
        color: rgba(0, 0, 0, 0.7);
        font-size: 0.9rem;
      }

      .context-icon {
        color: #1976d2;
        opacity: 0.9;
        font-size: 1.1rem;
        width: 1.1rem;
        height: 1.1rem;
      }

      /* Pronunciation Tab */
      .pronunciation-tab {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 1rem;
        min-height: 200px;
      }

      /* Conjugation Tab */
      .conjugation-table {
        display: flex;
        flex-direction: column;
        gap: 2rem;
      }

      .mood-section {
        margin-bottom: 2rem;
      }

      .mood-section h3 {
        color: var(--primary-color);
        margin-bottom: 1rem;
        font-size: 1.3rem;
        font-weight: 600;
      }

      .tense-section {
        margin-bottom: 1.5rem;
      }

      .tense-section h4 {
        color: var(--text-primary);
        margin-bottom: 0.5rem;
        font-size: 1.1rem;
        font-weight: 500;
      }

      .tense-section table {
        width: 100%;
        border-collapse: collapse;
      }

      .tense-section td {
        padding: 0.5rem;
        border-bottom: 1px solid var(--border-color);
      }

      .pronoun {
        font-weight: 500;
        color: var(--text-secondary);
        width: 40%;
      }

      .conjugation {
        color: var(--text-primary);
      }

      /* Metadata Footer */
      .metadata-footer {
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid var(--border-color);
        display: flex;
        justify-content: space-between;
        color: var(--text-secondary);
        font-size: 0.9rem;
        width: 100%;
      }

      .no-content {
        text-align: center;
        color: var(--text-secondary);
        font-style: italic;
        padding: 2rem;
      }

      /* Dark Theme Adjustments */
      .dark-theme {
        .word-card {
          background: var(--card-background);
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }

        .source-word {
          color: rgba(255, 255, 255, 0.87);
        }

        .target-word {
          color: var(--primary-light, #64b5f6);
        }

        .pronunciation {
          color: rgba(255, 255, 255, 0.6);
        }

        .add-to-list-button {
          color: var(--primary-light, #64b5f6);
          border-color: var(--primary-light, #64b5f6) !important;

          &:hover {
            background-color: rgba(100, 181, 246, 0.1) !important;
          }
        }

        .pos-tag {
          color: var(--primary-light, #64b5f6);
          background-color: rgba(100, 181, 246, 0.1);
        }

        .usage-hint {
          color: rgba(255, 255, 255, 0.7);
          background-color: rgba(255, 255, 255, 0.05);
        }

        .hint-icon {
          color: var(--primary-light, #64b5f6);
        }

        .definitions {
          color: rgba(255, 255, 255, 0.87);
        }

        .definitions li {
          background-color: rgba(255, 255, 255, 0.03);

          &:hover {
            background-color: rgba(255, 255, 255, 0.05);
          }
        }

        .definition-number {
          color: var(--primary-light, #64b5f6);
        }

        .single-definition {
          background-color: rgba(255, 255, 255, 0.03);
        }

        .synonym-item {
          background-color: rgba(255, 255, 255, 0.03);
          border-left-color: var(--primary-light, #64b5f6);
        }

        .synonym-header {
          background-color: rgba(255, 255, 255, 0.02);
          border-bottom-color: rgba(255, 255, 255, 0.1);
        }

        .synonym-number,
        .synonym-word {
          color: var(--primary-light, #64b5f6);
        }

        .synonym-explanation {
          color: rgba(255, 255, 255, 0.7);
        }

        .example-item {
          background-color: rgba(255, 255, 255, 0.03);
        }

        .example-text {
          background-color: rgba(255, 255, 255, 0.02);
          border-bottom-color: rgba(255, 255, 255, 0.1);
        }

        .source-example {
          color: rgba(255, 255, 255, 0.87);
        }

        .target-example {
          color: rgba(255, 255, 255, 0.7);
          border-left-color: rgba(255, 255, 255, 0.1);
        }

        .example-context {
          color: rgba(255, 255, 255, 0.7);
          background-color: rgba(255, 255, 255, 0.05);
        }

        .context-icon {
          color: var(--primary-light, #64b5f6);
        }

        .mood-section h3 {
          color: var(--primary-light, #64b5f6);
        }

        .tense-section h4 {
          color: rgba(255, 255, 255, 0.87);
        }

        .tense-section td {
          border-bottom-color: rgba(255, 255, 255, 0.1);
        }

        .pronoun {
          color: rgba(255, 255, 255, 0.6);
        }

        .conjugation {
          color: rgba(255, 255, 255, 0.87);
        }

        .metadata-footer {
          color: rgba(255, 255, 255, 0.6);
          border-top-color: rgba(255, 255, 255, 0.1);
        }

        .no-content {
          color: rgba(255, 255, 255, 0.6);
        }

        .language-flags {
          background-color: rgba(100, 181, 246, 0.1);
        }

        .arrow-icon {
          color: rgba(255, 255, 255, 0.7);
        }

        ::ng-deep {
          .mat-mdc-tab-group {
            .mat-mdc-tab-header {
              background: transparent;
            }

            .mdc-tab {
              opacity: 0.7;
              transition: all 0.2s ease;

              &:hover {
                opacity: 0.9;
                background-color: rgba(255, 255, 255, 0.08);
              }

              &--active {
                opacity: 1;

                &:hover {
                  background-color: rgba(100, 181, 246, 0.08);
                }
              }

              .mdc-tab__text-label {
                color: rgba(255, 255, 255, 0.87) !important;
              }

              .mat-icon {
                color: rgba(255, 255, 255, 0.87) !important;
              }
            }

            .mdc-tab--active {
              .mdc-tab__text-label {
                color: var(--primary-light, #64b5f6) !important;
              }

              .mat-icon {
                color: var(--primary-light, #64b5f6) !important;
              }
            }

            .mdc-tab-indicator__content--underline {
              border-color: var(--primary-light, #64b5f6) !important;
            }

            .mat-mdc-tab-header-pagination {
              color: rgba(255, 255, 255, 0.87);
              background: transparent;

              &-disabled {
                color: rgba(255, 255, 255, 0.3);
              }

              &:hover:not(.mat-mdc-tab-header-pagination-disabled) {
                background: transparent;
              }

              &-chevron {
                border-color: currentColor;
              }
            }
          }
        }
      }

      /* Responsive Design */
      @media (max-width: 768px) {
        .word-card-container {
          padding: 1rem;
        }

        .word-card {
          padding: 1.25rem;
        }

        .word-header {
          flex-direction: row;
          align-items: flex-start;
          gap: 1rem;
          margin-bottom: 1.5rem;
        }

        .word-title-section {
          gap: 0.2rem;
        }

        .source-word {
          font-size: 2rem;
        }

        .target-word {
          font-size: 1.5rem;
        }

        .add-to-list-button {
          position: static;
          width: auto;
          margin-left: auto;
        }

        .header-content {
          flex-direction: column;
          gap: 1.5rem;
        }

        .media-section {
          width: 100%;
          margin-top: 0;
          order: -1;
        }

        .word-image {
          max-height: 200px;
          object-fit: cover;
        }

        .content-tabs {
          margin-top: 1.5rem;
        }

        .language-flag {
          font-size: 0.875rem;
        }

        .arrow-icon {
          font-size: 0.875rem;
          width: 0.875rem;
          height: 0.875rem;
        }

        ::ng-deep {
          .mat-mdc-tab-header {
            margin: 0 -1.25rem;
            padding: 0 1.25rem;
            width: calc(100% + 2.5rem);
          }

          .mat-mdc-tab {
            min-width: auto;
            padding: 0 12px;
          }

          .mat-mdc-tab-label-content {
            font-size: 0.9rem;
          }

          .mat-mdc-tab-header-pagination {
            min-width: 28px;
          }
        }

        .definitions li,
        .synonym-item,
        .example-item {
          padding: 0.75rem;
        }

        .conjugation-table {
          overflow-x: auto;
          margin: 0 -1.25rem;
          padding: 0 1.25rem;
          width: calc(100% + 2.5rem);

          table {
            min-width: 500px;
          }
        }
      }

      @media (max-width: 480px) {
        .word-card-container {
          padding: 0.5rem;
        }

        .word-card {
          padding: 1rem;
          border-radius: 8px;
        }

        .word-title-section {
          gap: 0.15rem;
        }

        .source-word {
          font-size: 1.75rem;
        }

        .target-word {
          font-size: 1.25rem;
        }

        .pronunciation {
          font-size: 0.9rem;
        }

        .pos-tags {
          flex-wrap: wrap;
        }

        .pos-tag {
          font-size: 0.8rem;
          height: 20px;
          padding: 0.25rem 0.5rem;
        }

        .usage-hint {
          font-size: 0.85rem;
          padding: 0.5rem;
        }

        .tab-content {
          padding: 1rem 0;
        }

        .language-flag {
          font-size: 1rem;
        }

        .arrow-icon {
          font-size: 0.8rem;
          width: 0.8rem;
          height: 0.8rem;
        }

        ::ng-deep {
          .mat-mdc-tab-header {
            margin: 0 -1rem;
            padding: 0 1rem;
            width: calc(100% + 2rem);
          }

          .mat-mdc-tab {
            padding: 0 8px;
          }

          .mat-mdc-tab-label-content {
            font-size: 0.85rem;
          }

          .mat-mdc-tab-header-pagination {
            min-width: 24px;

            &-before,
            &-after {
              padding: 0 4px;
            }
          }
        }

        .definitions li,
        .synonym-item,
        .example-item {
          padding: 0.625rem;
          font-size: 0.9rem;
        }

        .example-context {
          font-size: 0.85rem;
          padding: 0.5rem 0.75rem;
        }

        .metadata-footer {
          flex-direction: row;
          justify-content: space-between;
          align-items: center;
          gap: 0.5rem;
          font-size: 0.8rem;
        }

        .word-header {
          flex-direction: row;
        }

        .add-to-list-button {
          padding: 0.4rem 1rem;
          font-size: 0.9rem;
        }

        .conjugation-table {
          margin: 0 -1rem;
          padding: 0 1rem;
          width: calc(100% + 2rem);

          h3 {
            font-size: 1.1rem;
          }

          h4 {
            font-size: 1rem;
          }

          td {
            padding: 0.375rem;
            font-size: 0.9rem;
          }
        }

        .language-flags {
          padding: 0.25rem 0.5rem;
          height: 20px;
        }

        .language-flag {
          font-size: 1rem;
        }

        .arrow-icon {
          font-size: 0.8rem;
          width: 0.8rem;
          height: 0.8rem;
        }

        .pos-tag {
          font-size: 0.8rem;
          height: 20px;
          padding: 0.25rem 0.5rem;
        }
      }
    `,
  ],
})
export class WordCard implements OnInit {
  themeService = inject(ThemeService);
  translationService = inject(TranslationService);
  wordService = inject(WordService);
  route = inject(ActivatedRoute);

  word: VocabularyWord | null = null;
  loading = true;
  error: string | null = null;

  ngOnInit() {
    // Get parameters from route
    const sourceLanguage = this.route.snapshot.paramMap.get('sourceLanguage');
    const targetLanguage = this.route.snapshot.paramMap.get('targetLanguage');
    const word = this.route.snapshot.paramMap.get('word');

    if (false) {
      //   this.loadWord(sourceLanguage, targetLanguage, word);
    } else {
      // For development, load mock data
      this.word = this.wordService.getMockWord();
      this.loading = false;
    }
  }

  loadWord(sourceLanguage: string, targetLanguage: string, word: string) {
    this.loading = true;
    this.error = null;

    this.wordService.getWord(sourceLanguage, targetLanguage, word).subscribe({
      next: (data) => {
        if (data) {
          this.word = data;
        } else {
          this.error = this.translationService.translate('wordCard.notFound');
        }
        this.loading = false;
      },
      error: (err) => {
        this.error = this.translationService.translate('wordCard.loadError');
        this.loading = false;
      },
    });
  }

  playPronunciation() {
    if (this.word?.pronunciation_url) {
      const audio = new Audio(this.word.pronunciation_url);
      audio.play().catch((err) => {
        console.error('Error playing audio:', err);
      });
    }
  }

  getPartOfSpeechLabel(pos: string): string {
    return this.translationService.translate(`wordCard.pos.${pos}`) || pos;
  }

  getIndicativeTenses(): string[] {
    if (!this.word?.conjugation_table?.indicativo) return [];
    return Object.keys(this.word.conjugation_table.indicativo);
  }

  getSubjunctiveTenses(): string[] {
    if (!this.word?.conjugation_table?.subjuntivo) return [];
    return Object.keys(this.word.conjugation_table.subjuntivo);
  }

  getConjugationPronouns(mood: string, tense: string): string[] {
    if (!this.word?.conjugation_table) return [];
    const moodData = this.word.conjugation_table[mood];
    if (!moodData?.[tense]) return [];
    return Object.keys(moodData[tense]);
  }

  getConjugationTenseLabel(tense: string): string {
    return (
      this.translationService.translate(
        `wordCard.conjugationData.tenses.${tense}`
      ) || tense
    );
  }

  getPronounLabel(pronoun: string): string {
    return (
      this.translationService.translate(
        `wordCard.conjugationData.pronouns.${pronoun}`
      ) || pronoun
    );
  }

  formatDate(dateString: string | undefined): string {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString(
      this.translationService.getCurrentLanguage()().code,
      {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      }
    );
  }

  goBack() {
    window.history.back();
  }

  isArray(value: any): boolean {
    return Array.isArray(value);
  }

  asArray(value: string | string[]): string[] {
    return value as string[];
  }

  getLanguageFlag(langCode: string | undefined): string {
    if (!langCode) return '';

    const flagMap: { [key: string]: string } = {
      en: '🇬🇧',
      es: '🇪🇸',
      de: '🇩🇪',
    };

    return flagMap[langCode.toLowerCase()] || langCode.toUpperCase();
  }
}
