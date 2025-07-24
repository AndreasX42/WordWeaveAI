import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { TranslatePipe } from '@/shared/pipes/translate.pipe';
import { VocabularyWord } from '@/models/word.model';

export interface ProcessingStage {
  id: string;
  name: string;
  icon: string;
  status: 'pending' | 'active' | 'completed' | 'failed';
  category: 'sequential' | 'parallel' | 'final';
  order: number;
  description: string;
}

@Component({
  selector: 'app-processing-stages',
  templateUrl: './processing-stages.html',
  styleUrls: ['./processing-stages.scss'],
  standalone: true,
  imports: [CommonModule, MatIconModule, TranslatePipe],
})
export class ProcessingStagesComponent {
  @Input() processingStages!: ProcessingStage[];
  @Input() word!: VocabularyWord;
  @Input() isRequestMode!: boolean;

  getVisibleStages(): ProcessingStage[] {
    return this.processingStages.filter((stage) => {
      if (stage.id === 'conjugation') {
        if (this.isRequestMode) {
          return true;
        }
        return this.word?.target_pos === 'verb' || this.word?.conjugation_table;
      }
      if (
        stage.id === 'synonyms' &&
        this.word?.target_pos &&
        !this.isRequestMode &&
        !this.shouldHaveSynonyms(this.word.target_pos)
      ) {
        return false;
      }
      return true;
    });
  }

  private shouldHaveSynonyms(pos: string): boolean {
    const posWithSynonyms = [
      'noun',
      'feminine noun',
      'masculine noun',
      'neuter noun',
      'verb',
      'adjective',
      'adverb',
      'interjection',
      'conjunction',
    ];
    return posWithSynonyms.includes(pos.toLowerCase());
  }
}
