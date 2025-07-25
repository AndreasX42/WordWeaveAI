import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { VocabularyWord } from '@/models/word.model';
import { Configs } from '@/shared/config';
import { LoadingStates } from './word-details';

@Component({
  selector: 'app-word-media',
  templateUrl: './word-media.html',
  styleUrls: ['./word-media.scss'],
  standalone: true,
  imports: [CommonModule],
})
export class WordMediaComponent {
  @Input() word!: VocabularyWord;
  @Input() loadingStates!: LoadingStates;
  @Input() isRequestMode!: boolean;
  @Input() hasMedia!: boolean;

  getS3Url(key: string | undefined): string {
    if (!key) return '';

    if (key.startsWith('http://') || key.startsWith('https://')) {
      return key;
    }

    const cleanKey = key.startsWith('/') ? key.slice(1) : key;

    return `${Configs.S3_BASE_URL}${cleanKey}`;
  }
}
