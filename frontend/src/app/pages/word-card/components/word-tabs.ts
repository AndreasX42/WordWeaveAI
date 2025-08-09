import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTabsModule } from '@angular/material/tabs';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TranslatePipe } from '@/shared/pipes/translate.pipe';
import {
  VocabularyWord,
  ConjugationTable,
  NonPersonalForms,
  Mood,
  Tense,
} from '@/models/word.model';
import { LanguageConfig } from '../conjugation.config';
import { LoadingStates } from './word-details';

@Component({
  selector: 'app-word-tabs',
  templateUrl: './word-tabs.html',
  styleUrls: ['./word-tabs.scss'],
  standalone: true,
  imports: [
    CommonModule,
    MatTabsModule,
    MatIconModule,
    MatProgressSpinnerModule,
    TranslatePipe,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WordTabsComponent {
  @Input() word!: VocabularyWord;
  @Input() loadingStates!: LoadingStates;
  @Input() isRequestMode!: boolean;
  @Input() hasSynonyms!: boolean;
  @Input() hasExamples!: boolean;
  @Input() hasFormasNoPersonales!: boolean;
  @Input() langConfig!: LanguageConfig;

  isArray(value: unknown): value is unknown[] {
    return Array.isArray(value);
  }

  asArray(value: string | string[]): string[] {
    return value as string[];
  }

  shouldShowConjugationTab(): boolean {
    if (this.isRequestMode && this.loadingStates.conjugation) {
      return true;
    }

    if (this.word?.conjugation_table || this.word?.target_pos === 'verb') {
      return true;
    }

    if (this.isRequestMode && !this.word?.target_pos) {
      return true;
    }

    return false;
  }

  getLabel(key: string): string {
    if (key in this.langConfig.labels) {
      const labelKey = key as keyof LanguageConfig['labels'];
      const labelValue = this.langConfig.labels[labelKey];
      if (typeof labelValue === 'string') {
        return labelValue;
      }
    }
    if (key in this.langConfig.labels.tenses) {
      return this.langConfig.labels.tenses[key];
    }
    return key;
  }

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

  getGroupedTenses(mood: string): string[][] {
    const tenses =
      mood === this.getIndicativeMoodName()
        ? this.getIndicativeTenses()
        : this.getSubjunctiveTenses();

    const grouped: string[][] = [];
    for (let i = 0; i < tenses.length; i += 3) {
      grouped.push(tenses.slice(i, i + 3));
    }
    return grouped;
  }

  getConjugationPronouns(mood: string): string[] {
    const conjugationTable = this.getConjugationTable();
    const moodData = conjugationTable?.[mood] as Mood;
    if (!moodData) return [];

    const firstTense = Object.values(moodData)[0] as Tense;
    return firstTense ? Object.keys(firstTense) : [];
  }

  getPronounLabel(pronoun: string): string {
    return this.langConfig.labels.pronouns[pronoun] || pronoun;
  }

  getConjugationValueForTense(
    mood: string,
    tense: string,
    pronoun: string
  ): string {
    const conjugationTable = this.getConjugationTable();
    const moodData = conjugationTable?.[mood] as Mood;
    const tenseData = moodData?.[tense] as Tense;
    return tenseData?.[pronoun] || '';
  }

  private cachedConjSource: unknown | null = null;
  private cachedConjTable: ConjugationTable | null = null;

  getConjugationTable(): ConjugationTable | null {
    const source = this.word?.conjugation_table;
    if (!source) return null;

    if (this.cachedConjSource === source && this.cachedConjTable) {
      return this.cachedConjTable;
    }

    let parsed: ConjugationTable | null = null;
    if (typeof source === 'object') {
      parsed = source as ConjugationTable;
    } else if (typeof source === 'string') {
      try {
        parsed = JSON.parse(source) as ConjugationTable;
      } catch (error) {
        console.error('Error parsing conjugation table JSON:', error);
        parsed = null;
      }
    }

    this.cachedConjSource = source;
    this.cachedConjTable = parsed;
    return parsed;
  }

  getIndicativeMoodName(): string {
    return this.langConfig.moods.indicative;
  }

  getSubjunctiveMoodName(): string {
    return this.langConfig.moods.subjunctive;
  }

  getNonPersonalFormsKey(): string {
    return this.langConfig.nonPersonalForms.key;
  }

  getNonPersonalForms(): NonPersonalForms | null {
    const key = this.getNonPersonalFormsKey();
    const conjugationTable = this.getConjugationTable();
    return (conjugationTable?.[key] as NonPersonalForms) || null;
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
}
