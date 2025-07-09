import { Pipe, PipeTransform } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

@Pipe({
  name: 'highlight',
  standalone: true,
})
export class HighlightPipe implements PipeTransform {
  constructor(private sanitizer: DomSanitizer) {}

  transform(text: string, search: string): SafeHtml {
    if (!search) {
      return text;
    }
    try {
      const pattern = search.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); // escape regex
      const regex = new RegExp(`(${pattern})`, 'gi');
      const result = text.replace(regex, '<mark class="hl">$1</mark>');
      return this.sanitizer.bypassSecurityTrustHtml(result);
    } catch {
      return text;
    }
  }
}
