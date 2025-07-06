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
  templateUrl: './word-card.html',
  styleUrls: ['./word-card.scss'],
})
export class WordCard implements OnInit {
  themeService = inject(ThemeService);
  translationService = inject(TranslationService);
  wordService = inject(WordService);
  route = inject(ActivatedRoute);

  word: VocabularyWord | null = null;
  loading = true;
  error: string | null = null;

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
    return !!(this.word?.media && this.word.media.length > 0);
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
    const targetLang = this.word?.target_language;
    if (targetLang === 'es') {
      return !!this.word?.conjugation_table?.['indicativo'];
    } else if (targetLang === 'en') {
      return !!this.word?.conjugation_table?.['indicative'];
    } else if (targetLang === 'de') {
      return !!this.word?.conjugation_table?.['indikativ'];
    }
    return false;
  }

  get hasSubjuntivo() {
    const targetLang = this.word?.target_language;
    if (targetLang === 'es') {
      return !!this.word?.conjugation_table?.['subjuntivo'];
    } else if (targetLang === 'en') {
      return !!this.word?.conjugation_table?.['subjunctive'];
    } else if (targetLang === 'de') {
      return !!this.word?.conjugation_table?.['konjunktiv'];
    }
    return false;
  }

  get hasFormasNoPersonales() {
    const targetLang = this.word?.target_language;
    if (targetLang === 'es') {
      return !!this.word?.conjugation_table?.['formas_no_personales'];
    } else if (targetLang === 'en' || targetLang === 'de') {
      return !!this.word?.conjugation_table?.['non_personal_forms'];
    }
    return false;
  }

  // Helper methods to get correct mood names for each language
  getIndicativeMoodName(): string {
    const targetLang = this.word?.target_language;
    if (targetLang === 'es') return 'indicativo';
    if (targetLang === 'en') return 'indicative';
    if (targetLang === 'de') return 'indikativ';
    return 'indicativo'; // fallback
  }

  getSubjunctiveMoodName(): string {
    const targetLang = this.word?.target_language;
    if (targetLang === 'es') return 'subjuntivo';
    if (targetLang === 'en') return 'subjunctive';
    if (targetLang === 'de') return 'konjunktiv';
    return 'subjuntivo'; // fallback
  }

  getNonPersonalFormsKey(): string {
    const targetLang = this.word?.target_language;
    if (targetLang === 'es') return 'formas_no_personales';
    return 'non_personal_forms'; // for English and German
  }

  // Get non-personal forms data dynamically based on language
  getNonPersonalForms(): any {
    const key = this.getNonPersonalFormsKey();
    return this.word?.conjugation_table?.[key];
  }

  // Get specific non-personal form values
  getInfinitive(): string {
    const forms = this.getNonPersonalForms();
    const targetLang = this.word?.target_language;

    if (targetLang === 'es') {
      return forms?.['infinitivo'] || '';
    } else if (targetLang === 'en') {
      return forms?.['infinitive'] || '';
    } else if (targetLang === 'de') {
      return forms?.['infinitive'] || '';
    }
    return '';
  }

  getParticiple(): string {
    const forms = this.getNonPersonalForms();
    const targetLang = this.word?.target_language;

    if (targetLang === 'es') {
      return forms?.['participio'] || '';
    } else if (targetLang === 'en') {
      return forms?.['past_participle'] || '';
    } else if (targetLang === 'de') {
      return forms?.['partizip_perfekt'] || '';
    }
    return '';
  }

  getGerund(): string {
    const forms = this.getNonPersonalForms();
    const targetLang = this.word?.target_language;

    if (targetLang === 'es') {
      return forms?.['gerundio'] || '';
    } else if (targetLang === 'en') {
      return forms?.['present_participle'] || '';
    } else if (targetLang === 'de') {
      return forms?.['partizip_praesens'] || '';
    }
    return '';
  }

  // Get section header labels based on target language
  getNonPersonalFormsLabel(): string {
    const targetLang = this.word?.target_language;

    if (targetLang === 'es') {
      return 'Formas no personales';
    } else if (targetLang === 'en') {
      return 'Non-personal forms';
    } else if (targetLang === 'de') {
      return 'Unpersönliche Formen';
    }
    return 'Non-personal forms';
  }

  getIndicativeMoodLabel(): string {
    const targetLang = this.word?.target_language;

    if (targetLang === 'es') {
      return 'Indicativo';
    } else if (targetLang === 'en') {
      return 'Indicative';
    } else if (targetLang === 'de') {
      return 'Indikativ';
    }
    return 'Indicative';
  }

  getSubjunctiveMoodLabel(): string {
    const targetLang = this.word?.target_language;

    if (targetLang === 'es') {
      return 'Subjuntivo';
    } else if (targetLang === 'en') {
      return 'Subjunctive';
    } else if (targetLang === 'de') {
      return 'Konjunktiv';
    }
    return 'Subjunctive';
  }

  // Get individual form labels
  getInfinitiveLabel(): string {
    const targetLang = this.word?.target_language;

    if (targetLang === 'es') {
      return 'Infinitivo';
    } else if (targetLang === 'en') {
      return 'Infinitive';
    } else if (targetLang === 'de') {
      return 'Infinitiv';
    }
    return 'Infinitive';
  }

  getParticipleLabel(): string {
    const targetLang = this.word?.target_language;

    if (targetLang === 'es') {
      return 'Participio';
    } else if (targetLang === 'en') {
      return 'Participle';
    } else if (targetLang === 'de') {
      return 'Partizip';
    }
    return 'Participle';
  }

  getGerundLabel(): string {
    const targetLang = this.word?.target_language;

    if (targetLang === 'es') {
      return 'Gerundio';
    } else if (targetLang === 'en') {
      return 'Gerund';
    } else if (targetLang === 'de') {
      return 'Gerundium';
    }
    return 'Gerund';
  }

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
    if (!this.word?.conjugation_table) return [];

    const targetLang = this.word.target_language;
    const conjugationTable = this.word.conjugation_table;

    // Get the main indicative mood key for each language
    if (targetLang === 'es' && conjugationTable['indicativo']) {
      return Object.keys(conjugationTable['indicativo']);
    } else if (targetLang === 'en' && conjugationTable['indicative']) {
      return Object.keys(conjugationTable['indicative']);
    } else if (targetLang === 'de' && conjugationTable['indikativ']) {
      return Object.keys(conjugationTable['indikativ']);
    }

    return [];
  }

  getSubjunctiveTenses(): string[] {
    if (!this.word?.conjugation_table) return [];

    const targetLang = this.word.target_language;
    const conjugationTable = this.word.conjugation_table;

    // Get the subjunctive mood key for each language
    if (targetLang === 'es' && conjugationTable['subjuntivo']) {
      return Object.keys(conjugationTable['subjuntivo']);
    } else if (targetLang === 'en' && conjugationTable['subjunctive']) {
      return Object.keys(conjugationTable['subjunctive']);
    } else if (targetLang === 'de' && conjugationTable['konjunktiv']) {
      return Object.keys(conjugationTable['konjunktiv']);
    }

    return [];
  }

  getConjugationPronouns(mood: string, tense: string): string[] {
    if (!this.word?.conjugation_table) return [];

    const targetLang = this.word.target_language;
    const conjugationTable = this.word.conjugation_table;

    // Get pronouns based on language and access the conjugation data
    let moodData: any = null;

    if (targetLang === 'es') {
      moodData =
        mood === 'indicativo'
          ? conjugationTable['indicativo']
          : conjugationTable['subjuntivo'];
    } else if (targetLang === 'en') {
      moodData =
        mood === 'indicative'
          ? conjugationTable['indicative']
          : conjugationTable['subjunctive'];
    } else if (targetLang === 'de') {
      moodData =
        mood === 'indikativ'
          ? conjugationTable['indikativ']
          : conjugationTable['konjunktiv'];
    }

    if (moodData && moodData[tense]) {
      return Object.keys(moodData[tense]);
    }

    return [];
  }

  getConjugationTenseLabel(tense: string): string {
    const targetLang = this.word?.target_language;

    // Spanish tense labels
    if (targetLang === 'es') {
      const spanishLabels: { [key: string]: string } = {
        presente: 'Presente',
        preterito_perfecto_simple: 'Pretérito Perfecto Simple',
        preterito_imperfecto: 'Pretérito Imperfecto',
        preterito_perfecto_compuesto: 'Pretérito Perfecto Compuesto',
        preterito_pluscuamperfecto: 'Pretérito Pluscuamperfecto',
        futuro: 'Futuro',
        futuro_perfecto: 'Futuro Perfecto',
        condicional: 'Condicional',
        condicional_perfecto: 'Condicional Perfecto',
      };
      return spanishLabels[tense] || tense;
    }

    // English tense labels
    if (targetLang === 'en') {
      const englishLabels: { [key: string]: string } = {
        present: 'Present',
        past: 'Past',
        present_perfect: 'Present Perfect',
        past_perfect: 'Past Perfect',
        present_perfect_progressive: 'Present Perfect Progressive',
        past_perfect_progressive: 'Past Perfect Progressive',
        future: 'Future',
        future_perfect: 'Future Perfect',
      };
      return englishLabels[tense] || tense;
    }

    // German tense labels
    if (targetLang === 'de') {
      const germanLabels: { [key: string]: string } = {
        praesens: 'Präsens',
        praeteritum: 'Präteritum',
        perfekt: 'Perfekt',
        plusquamperfekt: 'Plusquamperfekt',
        futur_i: 'Futur I',
        futur_ii: 'Futur II',
        konjunktiv_i: 'Konjunktiv I',
        konjunktiv_ii: 'Konjunktiv II',
      };
      return germanLabels[tense] || tense;
    }

    return tense;
  }

  getPronounLabel(pronoun: string): string {
    const targetLang = this.word?.target_language;

    // Spanish pronoun labels
    if (targetLang === 'es') {
      const spanishLabels: { [key: string]: string } = {
        yo: 'Yo',
        tu: 'Tú',
        el_ella_usted: 'Él/Ella/Usted',
        nosotros_nosotras: 'Nosotros/Nosotras',
        vosotros_vosotras: 'Vosotros/Vosotras',
        ellos_ellas_ustedes: 'Ellos/Ellas/Ustedes',
      };
      return spanishLabels[pronoun] || pronoun;
    }

    // English pronoun labels
    if (targetLang === 'en') {
      const englishLabels: { [key: string]: string } = {
        I: 'I',
        you: 'You',
        he_she_it: 'He/She/It',
        we: 'We',
        you_plural: 'You (plural)',
        they: 'They',
      };
      return englishLabels[pronoun] || pronoun;
    }

    // German pronoun labels
    if (targetLang === 'de') {
      const germanLabels: { [key: string]: string } = {
        ich: 'Ich',
        du: 'Du',
        er_sie_es: 'Er/Sie/Es',
        wir: 'Wir',
        ihr: 'Ihr',
        sie: 'Sie',
      };
      return germanLabels[pronoun] || pronoun;
    }

    return pronoun;
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
