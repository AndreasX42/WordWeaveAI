import { Component, ChangeDetectionStrategy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { TranslationService } from '../services/translation.service';

interface FooterLink {
  labelKey: string;
  route: string;
  external?: boolean;
}

interface FooterSection {
  titleKey: string;
  key: string;
  links: FooterLink[];
}

@Component({
  selector: 'app-footer',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './footer.html',
  styleUrl: './footer.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Footer {
  private translationService = inject(TranslationService);

  currentYear = new Date().getFullYear();

  footerSections: FooterSection[] = [
    {
      titleKey: 'footer.quickLinks.title',
      key: 'quickLinks',
      links: [
        { labelKey: 'footer.quickLinks.home', route: '/' },
        { labelKey: 'footer.quickLinks.search', route: '/search' },
        { labelKey: 'footer.quickLinks.health', route: '/health' },
        { labelKey: 'footer.quickLinks.profile', route: '/profile' },
      ],
    },
    {
      titleKey: 'footer.account.title',
      key: 'account',
      links: [
        { labelKey: 'footer.account.login', route: '/login' },
        { labelKey: 'footer.account.register', route: '/register' },
        {
          labelKey: 'footer.account.forgotPassword',
          route: '/forgot-password',
        },
      ],
    },
    {
      titleKey: 'footer.support.title',
      key: 'support',
      links: [
        { labelKey: 'footer.support.help', route: '/help', external: true },
        {
          labelKey: 'footer.support.contact',
          route: '/contact',
          external: true,
        },
        {
          labelKey: 'footer.support.privacy',
          route: '/privacy',
          external: true,
        },
        { labelKey: 'footer.support.terms', route: '/terms', external: true },
      ],
    },
  ];

  onExternalLinkClick(event: Event): void {
    event.preventDefault();
    // Handle external link clicks or show coming soon message
    console.log('External link clicked - feature coming soon');
  }

  trackBySection(index: number, section: FooterSection): string {
    return section.key;
  }

  trackByLink(index: number, link: FooterLink): string {
    return link.route;
  }

  translate(key: string, params?: Record<string, string>): string {
    return this.translationService.translate(key, params);
  }
}
