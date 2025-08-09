import {
  Component,
  inject,
  OnInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  DestroyRef,
} from '@angular/core';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatOptionModule } from '@angular/material/core';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialogModule } from '@angular/material/dialog';
import { CommonModule } from '@angular/common';
import { ThemeService } from '../../services/theme.service';
import { TranslationService } from '../../services/translation.service';
import { WordService } from '../../services/word.service';
import {
  WordRequestService,
  WordRequestNotification,
} from '../../services/word-request.service';
import { MessageService } from '../../services/message.service';
import { MatDialog } from '@angular/material/dialog';
import {
  RequestWordDialogComponent,
  RequestWordDialogData,
  RequestWordDialogResult,
} from './request-word-dialog';
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
  map,
} from 'rxjs/operators';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Params } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
// View-model for precomputed template fields
type VocabularyWordView = VocabularyWord & {
  displayPos: string;
  sourceFlag: string;
  targetFlag: string;
};

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
    MatOptionModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    MatDialogModule,
    ReactiveFormsModule,
    CommonModule,
    TranslatePipe,
    HighlightPipe,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SearchComponent implements OnInit {
  themeService = inject(ThemeService);
  translationService = inject(TranslationService);
  wordService = inject(WordService);
  wordRequestService = inject(WordRequestService);
  messageService = inject(MessageService);
  dialog = inject(MatDialog);
  router = inject(Router);
  cdr = inject(ChangeDetectorRef);
  destroyRef = inject(DestroyRef);
  route = inject(ActivatedRoute);

  searchControl = new FormControl<string>('', { nonNullable: true });
  sourceLanguageControl = new FormControl<string>('', { nonNullable: true });
  targetLanguageControl = new FormControl<string>('', { nonNullable: true });

  // Manual search trigger for immediate searches (Enter key, search button)
  private manualSearchTrigger = new Subject<void>();

  // Flag to prevent searches during language swaps
  private isSwappingLanguages = false;

  loading = false;
  searchResults: VocabularyWordView[] = [];
  hasSearched = false;
  searchError: string | null = null;

  // Word request state
  requestingWord = false;

  // Note: Using reactive forms throughout - no need for ngModel bridges

  private readonly STORAGE_KEY_SOURCE = 'source_language';
  private readonly STORAGE_KEY_TARGET = 'target_language';

  // Memoization cache for flags
  private languageFlagCache = new Map<string, string>();

  // Removed unused breakpoint observer logic

  constructor() {
    this.loadLanguagePreferences();
    this.searchResults = [];
  }

  ngOnInit(): void {
    this.route.queryParams
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((params: Params) => {
        const query = params['query'];
        const source = params['source'];
        const target = params['target'];
        const autosearch = params['autosearch'];

        if (query) {
          this.searchControl.setValue(query);
        }

        if (source) {
          const sourceLang = this.translationService.languages.find(
            (lang) => lang.name === source || lang.code === source
          );
          if (sourceLang) {
            this.sourceLanguageControl.setValue(sourceLang.code);
          }
        }

        if (target) {
          const targetLang = this.translationService.languages.find(
            (lang) => lang.name === target || lang.code === target
          );
          if (targetLang) {
            this.targetLanguageControl.setValue(targetLang.code);
          }
        }

        if (autosearch === 'true' && query) {
          this.search();
        }
      });

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
      map(() => [
        this.searchControl.value,
        this.sourceLanguageControl.value,
        this.targetLanguageControl.value,
      ])
    );

    // Merge both streams - debounced and immediate
    const allSearchTriggers = merge(
      debouncedSearchTrigger,
      immediateSearchTrigger
    ).pipe(
      distinctUntilChanged(
        (a, b) => a[0] === b[0] && a[1] === b[1] && a[2] === b[2]
      )
    );

    // Main search logic
    allSearchTriggers
      .pipe(
        tap(() => {
          this.loading = true;
          this.searchResults = [];
          this.searchError = null;
          this.cdr.markForCheck();
        }),
        switchMap(([term, sourceLanguage, targetLanguage]) => {
          const trimmed = term?.trim() ?? '';
          if (trimmed === '') {
            this.hasSearched = false;
            this.loading = false;
            this.cdr.markForCheck();
            return of([]);
          }

          this.hasSearched = true;

          const sourceLanguageParam = sourceLanguage || undefined;
          const targetLanguageParam = targetLanguage || undefined;

          return this.wordService
            .searchWords(trimmed, sourceLanguageParam, targetLanguageParam)
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
          this.cdr.markForCheck();
        }),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe((results) => {
        const mapped: VocabularyWordView[] = (results || []).map((w) => ({
          ...w,
          displayPos: this.extractPosFromSk(w.sk),
          sourceFlag: this.translationService.getLanguageFlag(
            w.source_language
          ),
          targetFlag: this.translationService.getLanguageFlag(
            w.target_language
          ),
        }));
        this.searchResults = mapped;
        this.cdr.markForCheck();
      });

    // Listen to language changes for preference saving
    this.sourceLanguageControl.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        this.saveLanguagePreferences();
      });

    this.targetLanguageControl.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        this.saveLanguagePreferences();
      });

    // Subscribe to word request notifications
    this.wordRequestService.notifications$
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((notification) => {
        this.handleWordRequestNotification(notification);
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
    this.cdr.markForCheck();
  }

  openWord(word: VocabularyWord) {
    // Extract POS from SK: "TGT#es#POS#noun" -> "noun"
    const posFromSk = this.extractPosFromSk(word.sk);

    // Ensure we use language codes, not full language names in URLs
    const sourceLanguageCode = this.getLanguageCode(word.source_language);
    const targetLanguageCode = this.getLanguageCode(word.target_language);

    this.router.navigate(
      [
        '/words',
        sourceLanguageCode,
        targetLanguageCode,
        posFromSk,
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

  // Convert language name or code to proper language code
  private getLanguageCode(language: string): string {
    // If it's already a code, return it
    if (language.length <= 3) {
      return language.toLowerCase();
    }

    // Convert full language names to codes
    const languageMap: Record<string, string> = {
      English: 'en',
      Spanish: 'es',
      German: 'de',
      english: 'en',
      spanish: 'es',
      german: 'de',
    };

    return languageMap[language] || language.toLowerCase().slice(0, 2);
  }

  // Extract POS from SK format: "TGT#es#POS#noun" -> "noun"
  private extractPosFromSk(sk: string): string {
    const parts = sk.split('#');
    const posIndex = parts.findIndex((part) => part === 'POS');
    if (posIndex !== -1 && posIndex + 1 < parts.length) {
      return parts[posIndex + 1];
    }
    return 'unknown';
  }

  // Get POS for display in search results (from SK)
  getDisplayPos(word: VocabularyWord): string {
    return this.extractPosFromSk(word.sk);
  }

  getLanguageFlag(code: string): string {
    if (this.languageFlagCache.has(code)) {
      return this.languageFlagCache.get(code)!;
    }
    const language = this.translationService.languages.find(
      (lang) => lang.code === code
    );
    const flag = language?.flag || '🏳️';
    this.languageFlagCache.set(code, flag);
    return flag;
  }

  // TrackBy for result list
  trackWord(index: number, word: VocabularyWord) {
    return word.pk && word.sk
      ? `${word.pk}|${word.sk}`
      : `${word.source_word}|${word.target_word}`;
  }

  // Removed redundant requestWord method - using dialog-based approach only

  private handleWordRequestNotification(
    notification: WordRequestNotification
  ): void {
    console.log('Word request notification:', notification);

    switch (notification.status) {
      case 'completed':
        // Optionally refresh search results
        if (this.searchControl.value?.trim()) {
          this.manualSearchTrigger.next();
        }
        break;
      case 'failed':
        this.messageService.showErrorMessage('search.requestWord.error');
        break;
      case 'processing':
        this.messageService.showInfoMessage('search.requestWord.requesting');
        break;
    }
  }

  // Check if request button should be shown
  shouldShowRequestButton(): boolean {
    return (
      this.hasSearched &&
      !this.loading &&
      !this.searchError &&
      this.searchControl.value?.trim() !== ''
    );
  }

  // Check if the exact word already exists in search results
  get wordAlreadyExists(): boolean {
    const searchTerm = this.searchControl.value?.trim().toLowerCase();
    if (!searchTerm) return false;

    return this.searchResults.some(
      (result) => result.source_word.toLowerCase() === searchTerm
    );
  }

  // Open request word dialog
  openRequestDialog(): void {
    const searchTerm = this.searchControl.value?.trim();
    if (!searchTerm) return;

    const dialogData: RequestWordDialogData = {
      searchTerm,
      currentResults: this.searchResults,
      sourceLanguage: this.sourceLanguageControl.value,
      targetLanguage: this.targetLanguageControl.value,
    };

    const dialogRef = this.dialog.open(RequestWordDialogComponent, {
      data: dialogData,
      width: '500px',
      maxWidth: '90vw',
      disableClose: false,
    });

    dialogRef
      .afterClosed()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((result: RequestWordDialogResult | undefined) => {
        if (result) {
          this.submitWordRequest(result);
        }
      });
  }

  // Submit word request from dialog and navigate to word card
  private submitWordRequest(result: RequestWordDialogResult): void {
    // Navigate to protected route first - this will trigger auth guard if needed
    this.router.navigate(['/words/request'], {
      state: {
        isRequest: true,
        requestData: result,
      },
    });
  }
}
