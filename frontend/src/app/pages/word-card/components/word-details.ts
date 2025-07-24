import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { VocabularyWord } from '@/models/word.model';

export interface LoadingStates {
  targetWord: boolean;
  syllables: boolean;
  pronunciation: boolean;
  definition: boolean;
  synonyms: boolean;
  examples: boolean;
  media: boolean;
  conjugation: boolean;
  languageInfo: boolean;
  sourcePos: boolean;
  targetPos: boolean;
}

@Component({
  selector: 'app-word-details',
  templateUrl: './word-details.html',
  styleUrls: ['./word-details.scss'],
  standalone: true,
  imports: [CommonModule, MatIconModule],
})
export class WordDetailsComponent {
  @Input() word!: VocabularyWord;
  @Input() loadingStates!: LoadingStates;
  @Input() isRequestMode!: boolean;

  getLanguageFlag(langCode: string | undefined): string {
    if (!langCode) return '';

    const lang = langCode.toLowerCase();

    const flagMap: Record<string, string> = {
      en: '🇬🇧',
      english: '🇬🇧',
      es: '🇪🇸',
      spanish: '🇪🇸',
      de: '🇩🇪',
      german: '🇩🇪',
    };

    return flagMap[lang] || langCode.toUpperCase();
  }
}
