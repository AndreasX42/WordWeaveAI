import { Component, inject, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
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
import {
  VocabularyWord,
  ConjugationTable,
  NonPersonalForms,
  Mood,
} from '../../models/word.model';
import { getLanguageConfig, LanguageConfig } from './conjugation.config';
import { AppConfig } from '../../shared/config';

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
  templateUrl: './word-card.html',
  styleUrls: ['./word-card.scss'],
})
export class WordCard implements OnInit {
  themeService = inject(ThemeService);
  translationService = inject(TranslationService);
  wordService = inject(WordService);
  route = inject(ActivatedRoute);
  router = inject(Router);

  word: VocabularyWord | null = null;
  loading = true;
  error: string | null = null;
  langConfig: LanguageConfig = getLanguageConfig(null);

  // Computed properties for performance optimization
  get indicativeTenses() {
    return this.getIndicativeTenses();
  }

  get subjunctiveTenses() {
    return this.getSubjunctiveTenses();
  }

  get hasTargetSyllables() {
    return !!(
      this.word?.target_syllables && this.word.target_syllables.length > 0
    );
  }

  get hasMedia() {
    return !!this.word?.media;
  }

  get hasSynonyms() {
    return !!(this.word?.synonyms && this.word.synonyms.length > 0);
  }

  get hasExamples() {
    return !!(this.word?.examples && this.word.examples.length > 0);
  }

  get hasConjugationTable() {
    return !!this.word?.conjugation_table;
  }

  get hasIndicativo() {
    const conjugationTable = this.getConjugationTable();
    return !!conjugationTable?.[this.langConfig.moods.indicative];
  }

  get hasSubjuntivo() {
    const conjugationTable = this.getConjugationTable();
    return !!conjugationTable?.[this.langConfig.moods.subjunctive];
  }

  get hasFormasNoPersonales() {
    const conjugationTable = this.getConjugationTable();
    return !!conjugationTable?.[this.langConfig.nonPersonalForms.key];
  }

  // Helper method to get properly parsed conjugation table
  getConjugationTable(): ConjugationTable | null {
    if (!this.word?.conjugation_table) return null;

    if (typeof this.word.conjugation_table === 'object') {
      return this.word.conjugation_table as ConjugationTable;
    }

    if (typeof this.word.conjugation_table === 'string') {
      try {
        return JSON.parse(this.word.conjugation_table) as ConjugationTable;
      } catch (error) {
        console.error('Error parsing conjugation table JSON:', error);
        return null;
      }
    }

    return null;
  }

  // Helper methods to get correct mood names for each language
  getIndicativeMoodName(): string {
    return this.langConfig.moods.indicative;
  }

  getSubjunctiveMoodName(): string {
    return this.langConfig.moods.subjunctive;
  }

  getNonPersonalFormsKey(): string {
    return this.langConfig.nonPersonalForms.key;
  }

  // Get non-personal forms data dynamically based on language
  getNonPersonalForms(): NonPersonalForms | null {
    const key = this.getNonPersonalFormsKey();
    const conjugationTable = this.getConjugationTable();
    return (conjugationTable?.[key] as NonPersonalForms) || null;
  }

  // Get specific non-personal form values
  getInfinitive(): string {
    const forms = this.getNonPersonalForms();
    const infinitiveKey = this.langConfig.nonPersonalForms.infinitive;
    return forms?.[infinitiveKey] || '';
  }

  getParticiple(): string {
    const forms = this.getNonPersonalForms();
    const participleKey = this.langConfig.nonPersonalForms.participle;
    return forms?.[participleKey] || '';
  }

  getGerund(): string {
    const forms = this.getNonPersonalForms();
    const gerundKey = this.langConfig.nonPersonalForms.gerund;
    return forms?.[gerundKey] || '';
  }

  // Get section header labels based on target language
  getNonPersonalFormsLabel(): string {
    return this.langConfig.labels.nonPersonalForms;
  }

  getIndicativeMoodLabel(): string {
    return this.langConfig.labels.indicativeMood;
  }

  getSubjunctiveMoodLabel(): string {
    return this.langConfig.labels.subjunctiveMood;
  }

  // Get individual form labels
  getInfinitiveLabel(): string {
    return this.langConfig.labels.infinitive;
  }

  getParticipleLabel(): string {
    return this.langConfig.labels.participle;
  }

  getGerundLabel(): string {
    return this.langConfig.labels.gerund;
  }

  ngOnInit() {
    // First check if word data was passed through route state
    const navigation = this.router.lastSuccessfulNavigation;
    const routeState = navigation?.extras?.state;

    if (routeState && routeState['word']) {
      // Use the word data passed from search results
      this.word = routeState['word'] as VocabularyWord;
      this.langConfig = getLanguageConfig(this.word);
      this.loading = false;
      return;
    }

    // Fallback: Get parameters from route and make API call
    const sourceLanguage = this.route.snapshot.paramMap.get('sourceLanguage');
    const targetLanguage = this.route.snapshot.paramMap.get('targetLanguage');
    const word = this.route.snapshot.paramMap.get('word');

    if (sourceLanguage && targetLanguage && word) {
      this.loadWord(sourceLanguage, targetLanguage, word);
    } else {
      // If parameters are missing, show error
      this.error =
        'Invalid parameters: missing source language, target language, or word';
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
          this.langConfig = getLanguageConfig(this.word);
        } else {
          this.error = this.translationService.translate('wordCard.notFound');
        }
        this.loading = false;
      },
      error: (err) => {
        console.error('API Error:', err);
        this.error = this.translationService.translate('wordCard.loadError');
        this.loading = false;
      },
    });
  }

  playPronunciation() {
    const url = this.getS3Url(this.word?.pronunciations.audio);
    if (url) {
      const audio = new Audio(url);
      audio.play().catch((err) => {
        console.error('Error playing audio:', err);
      });
    }
  }

  playSyllables() {
    const url = this.getS3Url(this.word?.pronunciations.syllables);
    if (url) {
      const audio = new Audio(url);
      audio.play().catch((err) => {
        console.error('Error playing syllable audio:', err);
      });
    }
  }

  getPartOfSpeechLabel(pos: string): string {
    return this.translationService.translate(`wordCard.pos.${pos}`) || pos;
  }

  getIndicativeTenses(): string[] {
    const conjugationTable = this.getConjugationTable();
    const indicativeMoodName = this.getIndicativeMoodName();
    const moodData = conjugationTable?.[indicativeMoodName];
    return moodData ? Object.keys(moodData) : [];
  }

  getSubjunctiveTenses(): string[] {
    const conjugationTable = this.getConjugationTable();
    const subjunctiveMoodName = this.getSubjunctiveMoodName();
    const moodData = conjugationTable?.[subjunctiveMoodName];
    return moodData ? Object.keys(moodData) : [];
  }

  getConjugationPronouns(mood: string, tense: string): string[] {
    const conjugationTable = this.getConjugationTable();
    if (!conjugationTable) {
      return [];
    }

    const moodData = conjugationTable[mood] as Mood;
    if (moodData?.[tense]) {
      return Object.keys(moodData[tense]);
    }

    return [];
  }

  getConjugationTenseLabel(tense: string): string {
    return this.langConfig.labels.tenses[tense] || tense;
  }

  getPronounLabel(pronoun: string): string {
    return this.langConfig.labels.pronouns[pronoun] || pronoun;
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

  // Helper methods for template to get conjugation values
  getConjugationValue(mood: string, tense: string, pronoun: string): string {
    const conjugationTable = this.getConjugationTable();
    if (!conjugationTable) return '';

    try {
      const moodData = conjugationTable[mood] as Mood;
      return moodData?.[tense]?.[pronoun] || '';
    } catch (error) {
      console.error('Error getting conjugation value:', error);
      return '';
    }
  }

  getS3Url(key: string | undefined): string {
    if (!key) {
      return '';
    }
    // If the key is already a full URL, return it
    if (key.startsWith('http')) {
      return key;
    }
    // Otherwise, construct the full URL
    return `${AppConfig.s3BaseUrl}${key}`;
  }
}
