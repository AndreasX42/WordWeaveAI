import { Pipe, PipeTransform, inject, signal, effect } from '@angular/core';
import { TranslationService } from '../../services/translation.service';

@Pipe({
  name: 'translate',
  pure: false,
  standalone: true,
})
export class TranslatePipe implements PipeTransform {
  private translationService = inject(TranslationService);
  private updateSignal = signal(0);

  constructor() {
    // React to language changes
    effect(() => {
      this.translationService.getCurrentLanguage()();
      this.updateSignal.update((val) => val + 1);
    });
  }

  transform(key: string, params?: Record<string, string>): string {
    // Access the signal to trigger updates
    this.updateSignal();
    return this.translationService.translate(key, params);
  }
}
