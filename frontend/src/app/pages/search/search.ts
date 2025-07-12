import { Component, inject, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatCardModule } from '@angular/material/card';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { ThemeService } from '../../services/theme.service';
import { TranslationService } from '../../services/translation.service';
import { WordService } from '../../services/word.service';
import { TranslatePipe } from '../../shared/pipes/translate.pipe';
import { HighlightPipe } from '../../shared/pipes/highlight.pipe';
import { VocabularyWord } from '../../models/word.model';
import { Subject, of, combineLatest, merge } from 'rxjs';
import {
  debounceTime,
  distinctUntilChanged,
  switchMap,
  catchError,
  tap,
  startWith,
  filter,
} from 'rxjs/operators';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { ChangeDetectorRef } from '@angular/core';
import { finalize } from 'rxjs/operators';

@Component({
  selector: 'app-search',
  templateUrl: './search.html',
  styleUrls: ['./search.scss'],
  standalone: true,
  imports: [
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatProgressSpinnerModule,
    MatCardModule,
    FormsModule,
    ReactiveFormsModule,
    CommonModule,
    TranslatePipe,
    HighlightPipe,
  ],
})
export class SearchComponent implements OnInit {
  themeService = inject(ThemeService);
  translationService = inject(TranslationService);
  wordService = inject(WordService);
  router = inject(Router);
  cdr = inject(ChangeDetectorRef);

  searchControl = new FormControl<string>('', { nonNullable: true });
  sourceLanguageControl = new FormControl<string>('', { nonNullable: true });
  targetLanguageControl = new FormControl<string>('', { nonNullable: true });

  // Manual search trigger for immediate searches (Enter key, search button)
  private manualSearchTrigger = new Subject<void>();

  // Flag to prevent searches during language swaps
  private isSwappingLanguages = false;

  loading = false;
  searchResults: VocabularyWord[] = [];
  hasSearched = false;
  searchError: string | null = null;

  // Note: Using reactive forms throughout - no need for ngModel bridges

  private readonly STORAGE_KEY_SOURCE = 'source_language';
  private readonly STORAGE_KEY_TARGET = 'target_language';

  private noResultsTimer: any;

  constructor() {
    this.loadLanguagePreferences();
    this.searchResults = [];
  }

  ngOnInit(): void {
    // Debounced search stream for automatic search (typing)
    const debouncedSearchTrigger = combineLatest([
      this.searchControl.valueChanges.pipe(
        startWith(this.searchControl.value),
        debounceTime(300),
        distinctUntilChanged()
      ),
      this.sourceLanguageControl.valueChanges.pipe(
        startWith(this.sourceLanguageControl.value),
        debounceTime(100),
        distinctUntilChanged()
      ),
      this.targetLanguageControl.valueChanges.pipe(
        startWith(this.targetLanguageControl.value),
        debounceTime(100),
        distinctUntilChanged()
      ),
    ]).pipe(
      // Filter out searches during language swaps
      filter(() => !this.isSwappingLanguages)
    );

    // Immediate search stream for manual triggers (Enter key, search button)
    const immediateSearchTrigger = this.manualSearchTrigger.pipe(
      switchMap(() =>
        of([
          this.searchControl.value,
          this.sourceLanguageControl.value,
          this.targetLanguageControl.value,
        ])
      )
    );

    // Merge both streams - debounced and immediate
    const allSearchTriggers = merge(
      debouncedSearchTrigger,
      immediateSearchTrigger
    );

    // Main search logic
    allSearchTriggers
      .pipe(
        tap(() => {
          this.loading = true;
          this.hasSearched = true;
          this.searchResults = [];
          this.searchError = null;
          this.cdr.detectChanges();
        }),
        switchMap(([term, sourceLanguage, targetLanguage]) => {
          if (!term.trim()) {
            this.hasSearched = false;
            return of([]);
          }

          const sourceLanguageParam = sourceLanguage || undefined;
          const targetLanguageParam = targetLanguage || undefined;

          return this.wordService
            .searchWords(term.trim(), sourceLanguageParam, targetLanguageParam)
            .pipe(
              catchError((error) => {
                console.error('Search error:', error);
                this.searchError =
                  'An error occurred during search. Please try again later.';
                return of([]);
              })
            );
        }),
        tap(() => {
          this.loading = false;
          this.cdr.detectChanges();
        }),
        finalize(() => {
          this.loading = false;
          this.cdr.detectChanges();
        })
      )
      .subscribe({
        next: (results) => {
          this.searchResults = results || [];
          if (!results || results.length === 0) {
            this.noResultsTimer = setTimeout(() => {
              this.hasSearched = false;
              this.cdr.detectChanges();
            }, 3500);
          }
        },
        error: (error) => {
          this.searchError =
            'An error occurred during search. Please try again later.';
          this.cdr.detectChanges();
        },
      });

    // Listen to language changes for preference saving
    this.sourceLanguageControl.valueChanges.subscribe(() => {
      this.saveLanguagePreferences();
    });

    this.targetLanguageControl.valueChanges.subscribe(() => {
      this.saveLanguagePreferences();
    });
  }

  private loadLanguagePreferences() {
    const savedSourceLanguage = localStorage.getItem(this.STORAGE_KEY_SOURCE);
    const savedTargetLanguage = localStorage.getItem(this.STORAGE_KEY_TARGET);

    if (savedSourceLanguage !== null) {
      this.sourceLanguageControl.setValue(savedSourceLanguage);
    }
    if (savedTargetLanguage !== null) {
      this.targetLanguageControl.setValue(savedTargetLanguage);
    }
  }

  private saveLanguagePreferences() {
    localStorage.setItem(
      this.STORAGE_KEY_SOURCE,
      this.sourceLanguageControl.value
    );
    localStorage.setItem(
      this.STORAGE_KEY_TARGET,
      this.targetLanguageControl.value
    );
  }

  swapLanguages() {
    const currentSource = this.sourceLanguageControl.value;
    const currentTarget = this.targetLanguageControl.value;

    // Set flag to prevent searches during swap
    this.isSwappingLanguages = true;

    this.sourceLanguageControl.setValue(currentTarget);
    this.targetLanguageControl.setValue(currentSource);

    // Clear cache when languages are swapped
    this.wordService.clearCaches();

    // Reset flag after a short delay to allow the debounced stream to settle
    setTimeout(() => {
      this.isSwappingLanguages = false;
      // Trigger a manual search if there's a search term
      if (this.searchControl.value?.trim()) {
        this.manualSearchTrigger.next();
      }
    }, 150);
  }

  search() {
    // Trigger immediate search via manual trigger
    this.manualSearchTrigger.next();
  }

  clearSearch(): void {
    this.searchControl.setValue('');
    this.searchResults = [];
    this.hasSearched = false;
    this.searchError = null;
    if (this.noResultsTimer) {
      clearTimeout(this.noResultsTimer);
    }
  }

  openWord(word: VocabularyWord) {
    this.router.navigate(
      [
        '/words',
        word.source_language,
        word.target_language,
        word.source_pos.toLowerCase().trim(),
        word.source_word.toLowerCase().trim(),
      ],
      {
        state: {
          pk: word.pk,
          sk: word.sk,
          word: word,
        },
      }
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

  // TrackBy for result list
  trackWord(index: number, word: VocabularyWord) {
    return word.source_word + word.target_word;
  }
}
