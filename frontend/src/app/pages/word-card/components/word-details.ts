import { Component, Input, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { VocabularyWord } from '@/models/word.model';
import { TranslationService } from '@/services/translation.service';

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
  translationService = inject(TranslationService);

  getLanguageFlag(langCode: string | undefined): string {
    return this.translationService.getLanguageFlag(langCode);
  }
}
