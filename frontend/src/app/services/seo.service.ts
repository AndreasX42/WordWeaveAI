import { Injectable, inject } from '@angular/core';
import { Meta, Title } from '@angular/platform-browser';
import { VocabularyWord } from '../models/word.model';

@Injectable({
  providedIn: 'root',
})
export class SEOService {
  private meta = inject(Meta);
  private title = inject(Title);

  updateWordPageSEO(word: VocabularyWord): void {
    // Dynamic title for individual word pages
    const pageTitle = `${word.source_word} in ${this.getLanguageName(
      word.target_language
    )} - ${word.target_word} | WordWeave`;
    this.title.setTitle(pageTitle);

    // Dynamic description
    const description = `Learn the ${this.getLanguageName(
      word.target_language
    )} translation of "${word.source_word}" - ${
      word.target_word
    }. Get AI-generated definitions, pronunciation, and examples with WordWeave.`;

    // Normalize POS for URL (e.g., "neuter noun" -> "noun")
    const normalizedPos = this.normalizePOS(word.source_pos);

    // Update meta tags
    this.meta.updateTag({ name: 'description', content: description });
    this.meta.updateTag({
      name: 'keywords',
      content: `${word.source_word}, ${
        word.target_word
      }, ${this.getLanguageName(
        word.source_language
      )} to ${this.getLanguageName(
        word.target_language
      )}, translation, definition, pronunciation`,
    });

    // Update Open Graph tags
    this.meta.updateTag({ property: 'og:title', content: pageTitle });
    this.meta.updateTag({ property: 'og:description', content: description });
    this.meta.updateTag({
      property: 'og:url',
      content: `https://wordweave.xyz/words/${word.source_language}/${word.target_language}/${normalizedPos}/${word.source_word}`,
    });

    // Update Twitter Card tags
    this.meta.updateTag({ name: 'twitter:title', content: pageTitle });
    this.meta.updateTag({ name: 'twitter:description', content: description });

    // Add structured data for educational content
    this.addWordStructuredData(word, normalizedPos);
  }

  private addWordStructuredData(
    word: VocabularyWord,
    normalizedPos: string
  ): void {
    // Remove existing structured data
    const existingScript = document.querySelector(
      'script[type="application/ld+json"][data-word-schema]'
    );
    if (existingScript) {
      existingScript.remove();
    }

    // Create new structured data for the word
    const structuredData = {
      '@context': 'https://schema.org',
      '@type': 'DefinedTerm',
      name: word.source_word,
      description: word.target_word,
      inDefinedTermSet: {
        '@type': 'DefinedTermSet',
        name: `${this.getLanguageName(
          word.source_language
        )} to ${this.getLanguageName(word.target_language)} Dictionary`,
        description: 'WordWeave AI-powered language learning vocabulary',
      },
      termCode: word.source_word,
      url: `https://wordweave.xyz/words/${word.source_language}/${word.target_language}/${normalizedPos}/${word.source_word}`,
      additionalType: 'https://schema.org/LinguisticSystem',
      inLanguage: word.source_language,
      about: {
        '@type': 'Language',
        name: this.getLanguageName(word.target_language),
        alternateName: word.target_language,
      },
    };

    // Add the structured data to the page
    const script = document.createElement('script');
    script.type = 'application/ld+json';
    script.setAttribute('data-word-schema', 'true');
    script.textContent = JSON.stringify(structuredData);
    document.head.appendChild(script);
  }

  resetToDefaultSEO(): void {
    // Reset to default home page SEO
    this.title.setTitle(
      'WordWeave - AI-Powered Language Learning & Vocabulary Builder'
    );
    this.meta.updateTag({
      name: 'description',
      content:
        "Learn languages faster with WordWeave's AI-powered vocabulary builder. Create personalized word lists, get AI-generated definitions, and master German, Spanish, and English vocabulary.",
    });
    this.meta.updateTag({
      property: 'og:title',
      content: 'WordWeave - AI-Powered Language Learning & Vocabulary Builder',
    });
    this.meta.updateTag({
      property: 'og:url',
      content: 'https://wordweave.xyz/',
    });

    // Remove word-specific structured data
    const wordSchema = document.querySelector(
      'script[type="application/ld+json"][data-word-schema]'
    );
    if (wordSchema) {
      wordSchema.remove();
    }
  }

  private getLanguageName(code: string): string {
    const languages: Record<string, string> = {
      en: 'English',
      de: 'German',
      es: 'Spanish',
    };
    return languages[code] || code;
  }

  private normalizePOS(pos: string): string {
    if (!pos) return 'pending';
    const posLower = pos.toLowerCase();
    return posLower.includes('noun') ? 'noun' : posLower;
  }
}
