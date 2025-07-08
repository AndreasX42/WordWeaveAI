import { VocabularyWord } from '../../models/word.model';

export interface LanguageConfig {
  moods: {
    indicative: string;
    subjunctive: string;
  };
  nonPersonalForms: {
    key: string;
    infinitive: string;
    participle: string;
    gerund: string;
  };
  labels: {
    nonPersonalForms: string;
    indicativeMood: string;
    subjunctiveMood: string;
    infinitive: string;
    participle: string;
    gerund: string;
    tenses: { [key: string]: string };
    pronouns: { [key: string]: string };
  };
}

export const languageConfigs: { [key: string]: LanguageConfig } = {
  es: {
    moods: {
      indicative: 'indicativo',
      subjunctive: 'subjuntivo',
    },
    nonPersonalForms: {
      key: 'formas_no_personales',
      infinitive: 'infinitivo',
      participle: 'participio',
      gerund: 'gerundio',
    },
    labels: {
      nonPersonalForms: 'Formas no personales',
      indicativeMood: 'Indicativo',
      subjunctiveMood: 'Subjuntivo',
      infinitive: 'Infinitivo',
      participle: 'Participio',
      gerund: 'Gerundio',
      tenses: {
        presente: 'Presente',
        preterito_perfecto_simple: 'Pretérito Perfecto Simple',
        preterito_imperfecto: 'Pretérito Imperfecto',
        preterito_perfecto_compuesto: 'Pretérito Perfecto Compuesto',
        preterito_pluscuamperfecto: 'Pretérito Pluscuamperfecto',
        futuro: 'Futuro',
        futuro_perfecto: 'Futuro Perfecto',
        condicional: 'Condicional',
        condicional_perfecto: 'Condicional Perfecto',
        // subjuntivo
        presente_de_subjuntivo: 'Presente de Subjuntivo',
        imperfecto_de_subjuntivo: 'Imperfecto de Subjuntivo',
        futuro_de_subjuntivo: 'Futuro de Subjuntivo',
        perfecto_de_subjuntivo: 'Perfecto de Subjuntivo',
        pluscuamperfecto_de_subjuntivo: 'Pluscuamperfecto de Subjuntivo',
      },
      pronouns: {
        yo: 'Yo',
        tu: 'Tú',
        el_ella_usted: 'Él/Ella/Usted',
        nosotros_nosotras: 'Nosotros/Nosotras',
        vosotros_vosotras: 'Vosotros/Vosotras',
        ellos_ellas_ustedes: 'Ellos/Ellas/Ustedes',
      },
    },
  },
  en: {
    moods: {
      indicative: 'indicative',
      subjunctive: 'subjunctive',
    },
    nonPersonalForms: {
      key: 'non_personal_forms',
      infinitive: 'infinitive',
      participle: 'past_participle',
      gerund: 'present_participle',
    },
    labels: {
      nonPersonalForms: 'Non-personal forms',
      indicativeMood: 'Indicative',
      subjunctiveMood: 'Subjunctive',
      infinitive: 'Infinitive',
      participle: 'Participle',
      gerund: 'Gerund',
      tenses: {
        present: 'Present',
        past: 'Past',
        present_perfect: 'Present Perfect',
        past_perfect: 'Past Perfect',
        present_perfect_progressive: 'Present Perfect Progressive',
        past_perfect_progressive: 'Past Perfect Progressive',
        future: 'Future',
        future_perfect: 'Future Perfect',
        future_progressive: 'Future Progressive',
        future_perfect_progressive: 'Future Perfect Progressive',
        conditional: 'Conditional',
        conditional_perfect: 'Conditional Perfect',
      },
      pronouns: {
        I: 'I',
        you: 'You',
        he_she_it: 'He/She/It',
        we: 'We',
        you_plural: 'You (plural)',
        they: 'They',
      },
    },
  },
  de: {
    moods: {
      indicative: 'indikativ',
      subjunctive: 'konjunktiv',
    },
    nonPersonalForms: {
      key: 'non_personal_forms',
      infinitive: 'infinitive',
      participle: 'partizip_perfekt',
      gerund: 'partizip_praesens',
    },
    labels: {
      nonPersonalForms: 'Unpersönliche Formen',
      indicativeMood: 'Indikativ',
      subjunctiveMood: 'Konjunktiv',
      infinitive: 'Infinitiv',
      participle: 'Partizip',
      gerund: 'Gerundium',
      tenses: {
        praesens: 'Präsens',
        praeteritum: 'Präteritum',
        perfekt: 'Perfekt',
        plusquamperfekt: 'Plusquamperfekt',
        futur_i: 'Futur I',
        futur_ii: 'Futur II',
        konjunktiv_i: 'Konjunktiv I',
        konjunktiv_ii: 'Konjunktiv II',
        konjunktiv_perfekt: 'Konjunktiv Perfekt',
      },
      pronouns: {
        ich: 'Ich',
        du: 'Du',
        er_sie_es: 'Er/Sie/Es',
        wir: 'Wir',
        ihr: 'Ihr',
        sie: 'Sie',
      },
    },
  },
};

export const DEFAULT_LANGUAGE_CONFIG = languageConfigs['en'];

export function getLanguageConfig(word: VocabularyWord | null): LanguageConfig {
  const lang = word?.target_language;
  return (lang && languageConfigs[lang]) || DEFAULT_LANGUAGE_CONFIG;
}
