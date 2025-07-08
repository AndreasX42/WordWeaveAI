import { Component, inject } from '@angular/core';
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
import { VocabularyWord } from '../../models/word.model';

@Component({
  selector: 'app-search',
  templateUrl: './search.html',
  styleUrls: ['./search.scss'],
  imports: [
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatProgressSpinnerModule,
    MatCardModule,
    FormsModule,
    CommonModule,
    TranslatePipe,
  ],
})
export class SearchComponent {
  themeService = inject(ThemeService);
  translationService = inject(TranslationService);
  wordService = inject(WordService);
  router = inject(Router);

  searchTerm = '';
  sourceLanguage = '';
  targetLanguage = '';
  loading = false;
  searchResults: VocabularyWord[] = [];
  hasSearched = false;

  private readonly STORAGE_KEY_SOURCE = 'source_language';
  private readonly STORAGE_KEY_TARGET = 'target_language';

  constructor() {
    this.loadLanguagePreferences();
    this.searchResults = [];
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

  onSearchInput() {
    // Optional: You can add real-time search here if needed
    // For now, we'll just search on enter or arrow button click
  }

  search() {
    if (!this.searchTerm.trim()) {
      return;
    }

    this.loading = true;
    this.hasSearched = true;

    const sourceLanguage = this.sourceLanguage || undefined;
    const targetLanguage = this.targetLanguage || undefined;

    this.wordService
      .searchWords(this.searchTerm.trim(), sourceLanguage, targetLanguage)
      .subscribe({
        next: (results) => {
          this.searchResults = results || [];
          this.loading = false;
        },
        error: (error) => {
          console.error('Search error:', error);
          this.searchResults = [];
          this.loading = false;
        },
      });
  }

  clearSearch() {
    this.searchTerm = '';
    this.searchResults = [];
    this.hasSearched = false;
    this.loading = false;
  }

  openWord(word: VocabularyWord) {
    this.router.navigate(
      [
        '/words',
        word.source_language,
        word.target_language,
        word.source_word.toLowerCase().trim(),
      ],
      {
        state: { word: word },
      }
    );
  }

  getLanguageName(code: string): string {
    const languages: { [key: string]: string } = {
      en: 'English',
      es: 'Spanish',
      de: 'German',
    };
    return languages[code] || code;
  }

  getLanguageFlag(code: string): string {
    const flags: { [key: string]: string } = {
      en: '🇺🇸',
      es: '🇪🇸',
      de: '🇩🇪',
    };
    return flags[code] || '🏳️';
  }
}
