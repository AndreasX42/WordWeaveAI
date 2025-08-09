import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'highlight',
  standalone: true,
})
export class HighlightPipe implements PipeTransform {
  private escapeHtml(value: string): string {
    return value
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  transform(text: string, search: string): string {
    if (!text) return '';
    if (!search) return this.escapeHtml(text);
    try {
      const pattern = search.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const regex = new RegExp(`(${pattern})`, 'gi');
      const escaped = this.escapeHtml(text);
      return escaped.replace(regex, '<mark class="hl">$1</mark>');
    } catch {
      return this.escapeHtml(text);
    }
  }
}
