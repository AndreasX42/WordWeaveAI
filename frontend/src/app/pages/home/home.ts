import { Component, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RouterLink } from '@angular/router';
import { ThemeService } from '../../services/theme.service';
import { TranslationService } from '../../services/translation.service';
import { TranslatePipe } from '../../shared/pipes/translate.pipe';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-home',
  standalone: true,
  template: `
    <div class="home-container" [class.dark-theme]="themeService.isDarkMode()">
      <!-- Hero Section -->
      <section class="hero-section">
        <div class="hero-content">
          <h1 class="hero-title">
            {{ 'home.hero.title' | translate }}
            <span class="highlight-text">{{
              'home.hero.titleHighlight' | translate
            }}</span>
          </h1>

          <p class="hero-subtitle">
            {{ 'home.hero.subtitle' | translate }}
          </p>

          <div class="hero-actions">
            <button
              mat-flat-button
              color="primary"
              class="cta-button"
              routerLink="/search"
            >
              <mat-icon>rocket_launch</mat-icon>
              {{ 'home.hero.ctaButton' | translate }}
            </button>
          </div>

          <!-- Stats moved higher and redesigned -->
          <div class="hero-stats">
            <div class="stats-grid">
              <div class="stat-item">
                <div class="stat-number">324</div>
                <div class="stat-label">
                  {{ 'home.hero.stats.wordsCreated' | translate }}
                </div>
              </div>
              <div class="stat-item">
                <div class="stat-number">47</div>
                <div class="stat-label">
                  {{ 'home.hero.stats.publicLists' | translate }}
                </div>
              </div>
              <div class="stat-item">
                <div class="stat-number">156</div>
                <div class="stat-label">
                  {{ 'home.hero.stats.activeUsers' | translate }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- How It Works Section -->
      <section class="how-it-works-section">
        <div class="how-it-works-container">
          <div class="section-header">
            <h2>{{ 'home.howItWorks.title' | translate }}</h2>
            <p>{{ 'home.howItWorks.subtitle' | translate }}</p>
          </div>

          <div class="steps-grid">
            <div class="step-card">
              <div class="step-number">1</div>
              <div class="step-icon">
                <mat-icon>library_add</mat-icon>
              </div>
              <h3>{{ 'home.howItWorks.step1.title' | translate }}</h3>
              <p>{{ 'home.howItWorks.step1.description' | translate }}</p>
            </div>

            <div class="step-card">
              <div class="step-number">2</div>
              <div class="step-icon">
                <mat-icon>auto_awesome</mat-icon>
              </div>
              <h3>{{ 'home.howItWorks.step2.title' | translate }}</h3>
              <p>{{ 'home.howItWorks.step2.description' | translate }}</p>
            </div>

            <div class="step-card">
              <div class="step-number">3</div>
              <div class="step-icon">
                <mat-icon>quiz</mat-icon>
              </div>
              <h3>{{ 'home.howItWorks.step3.title' | translate }}</h3>
              <p>{{ 'home.howItWorks.step3.description' | translate }}</p>
            </div>
          </div>
        </div>
      </section>

      <!-- Features Section (Condensed) -->
      <section class="features-section">
        <div class="features-container">
          <div class="section-header">
            <h2>{{ 'home.features.title' | translate }}</h2>
            <p>{{ 'home.features.subtitle' | translate }}</p>
          </div>

          <div class="features-grid">
            <div class="feature-card">
              <div class="feature-icon">
                <mat-icon>library_books</mat-icon>
              </div>
              <h3>{{ 'home.features.personalLists.title' | translate }}</h3>
              <p>{{ 'home.features.personalLists.description' | translate }}</p>
            </div>

            <div class="feature-card">
              <div class="feature-icon">
                <mat-icon>groups</mat-icon>
              </div>
              <h3>{{ 'home.features.communityDatabase.title' | translate }}</h3>
              <p>
                {{ 'home.features.communityDatabase.description' | translate }}
              </p>
            </div>

            <div class="feature-card">
              <div class="feature-icon">
                <mat-icon>visibility</mat-icon>
              </div>
              <h3>{{ 'home.features.aiGeneration.title' | translate }}</h3>
              <p>{{ 'home.features.aiGeneration.description' | translate }}</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  `,
  styles: [
    `
      .home-container {
        position: relative;
        overflow-x: hidden;
      }

      /* Dark theme section adjustments */
      .dark-theme .features-section {
        background: rgba(0, 0, 0, 0.02);
      }

      .dark-theme .how-it-works-section {
        background: rgba(0, 0, 0, 0.03);
      }

      /* Hero Section */
      .hero-section {
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        align-items: center;
        max-width: 1200px;
        margin: 0 auto;
        padding: 60px 2rem 50px;
        text-align: center;
        min-height: calc(100vh - 100px);
      }

      .hero-content {
        z-index: 1;
      }

      .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(var(--primary-color-rgb, 21, 101, 192), 0.1);
        color: var(--primary-color, #1565c0);
        padding: 8px 16px;
        border-radius: 24px;
        font-size: 0.875rem;
        font-weight: 500;
        margin-bottom: 24px;
        border: 1px solid rgba(var(--primary-color-rgb, 21, 101, 192), 0.2);
      }

      .hero-title {
        font-size: 3rem;
        font-weight: 700;
        line-height: 1.1;
        margin-bottom: 32px;
        color: var(--text-primary);
      }

      .highlight-text {
        background: linear-gradient(
          135deg,
          var(--primary-color, #1565c0) 0%,
          var(--accent-color, #ff4081) 100%
        );
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        position: relative;
      }

      .hero-subtitle {
        font-size: 1.2rem;
        color: var(--text-secondary);
        line-height: 1.5;
        margin-bottom: 24px;
        max-width: 580px;
        margin-left: auto;
        margin-right: auto;
      }

      .hero-actions {
        display: flex;
        gap: 16px;
        margin-bottom: 48px;
        justify-content: center;
      }

      .cta-button {
        background: linear-gradient(
          135deg,
          var(--primary-color, #1565c0) 0%,
          var(--primary-dark, #0d47a1) 100%
        ) !important;
        color: white !important;
        padding: 14px 32px !important;
        font-size: 16px !important;
        font-weight: 600 !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 20px rgba(var(--primary-color-rgb, 21, 101, 192), 0.3) !important;
        transition: all 0.3s ease !important;
      }

      .cta-button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(var(--primary-color-rgb, 21, 101, 192), 0.4) !important;
      }

      .hero-stats {
        margin-top: 60px;
        opacity: 0.9;
      }

      .stats-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 20px;
        max-width: 400px;
        margin: 0 auto;
      }

      .stat-item {
        padding: 12px 10px;
        background: var(--surface-color);
        border-radius: 12px;
        text-align: center;
        border: 1px solid var(--border-color);
        transition: all 0.3s ease;
      }

      .stat-item:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        border-color: var(--primary-color);
      }

      .stat-number {
        font-size: 1.8rem;
        font-weight: 700;
        margin-bottom: 4px;
        color: var(--primary-color);
        display: block;
      }

      .stat-label {
        font-size: 0.75rem;
        color: var(--text-secondary);
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }

      /* How It Works Section */
      .how-it-works-section {
        padding: 80px 2rem;
        position: relative;
        z-index: 1;
        background: rgba(255, 255, 255, 0.02);
      }

      .how-it-works-container {
        max-width: 1200px;
        margin: 0 auto;
      }

      .steps-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 32px;
        margin-top: 48px;
      }

      .step-card {
        position: relative;
        background: var(--card-background);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 32px 24px;
        text-align: center;
        transition: all 0.3s ease;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
      }

      .step-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.1);
        border-color: var(--primary-color);
      }

      .step-number {
        position: absolute;
        top: -12px;
        left: 24px;
        background: var(--primary-color);
        color: white;
        width: 24px;
        height: 24px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.875rem;
        font-weight: 600;
      }

      .step-icon {
        width: 64px;
        height: 64px;
        margin: 16px auto 20px;
        background: linear-gradient(
          135deg,
          var(--primary-color, #1565c0) 0%,
          var(--primary-light, #42a5f5) 100%
        );
        border-radius: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
      }

      .step-card h3 {
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: 12px;
        color: var(--text-primary);
      }

      .step-card p {
        color: var(--text-secondary);
        line-height: 1.5;
        font-size: 0.95rem;
      }

      /* Features Section */
      .features-section {
        padding: 80px 2rem;
        position: relative;
        z-index: 1;
        background: rgba(255, 255, 255, 0.01);
      }

      .features-container {
        max-width: 1200px;
        margin: 0 auto;
      }

      .section-header {
        text-align: center;
        margin-bottom: 64px;
      }

      .section-header h2 {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 16px;
        color: var(--text-primary);
      }

      .section-header p {
        font-size: 1.125rem;
        color: var(--text-secondary);
        max-width: 600px;
        margin: 0 auto;
      }

      .features-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 32px;
        max-width: 1000px;
        margin: 0 auto;
      }

      .secondary-cta {
        text-align: center;
        margin-top: 48px;
      }

      .secondary-button {
        padding: 14px 32px !important;
        font-size: 16px !important;
        border-radius: 12px !important;
        border: 2px solid var(--border-color) !important;
        color: var(--text-primary) !important;
        transition: all 0.3s ease !important;
      }

      .secondary-button:hover {
        border-color: var(--primary-color) !important;
        background: rgba(
          var(--primary-color-rgb, 21, 101, 192),
          0.05
        ) !important;
        transform: translateY(-2px) !important;
      }

      .feature-card {
        background: var(--card-background);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 32px;
        text-align: center;
        transition: all 0.5s ease;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
      }

      .feature-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.1);
        border-color: var(--primary-color);
      }

      .feature-icon {
        width: 64px;
        height: 64px;
        margin: 0 auto 24px;
        background: linear-gradient(
          135deg,
          var(--primary-color, #1565c0) 0%,
          var(--primary-light, #42a5f5) 100%
        );
        border-radius: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
      }

      .feature-card h3 {
        font-size: 1.5rem;
        font-weight: 600;
        margin-bottom: 16px;
        color: var(--text-primary);
      }

      .feature-card p {
        color: var(--text-secondary);
        line-height: 1.6;
      }

      /* Mobile Responsive */
      @media (max-width: 768px) {
        .hero-section {
          padding: 30px 1rem 30px;
          min-height: calc(100vh - 100px);
        }

        .hero-title {
          font-size: 2.2rem;
          margin-bottom: 24px;
        }

        .hero-subtitle {
          font-size: 1.1rem;
        }

        .hero-actions {
          flex-direction: column;
          align-items: center;
        }

        .cta-button {
          width: 100%;
          max-width: 280px;
        }

        .stats-grid {
          grid-template-columns: repeat(3, 1fr);
          gap: 12px;
          max-width: 350px;
        }

        .stat-item {
          padding: 12px 8px;
        }

        .stat-number {
          font-size: 1.4rem;
        }

        .stat-label {
          font-size: 0.7rem;
        }

        .steps-grid {
          grid-template-columns: 1fr;
          gap: 24px;
        }

        .step-card {
          padding: 24px 20px;
        }

        .section-header h2 {
          font-size: 2rem;
        }

        .features-grid {
          grid-template-columns: 1fr;
          gap: 20px;
        }
      }

      @media (max-width: 480px) {
        .hero-section {
          padding: 20px 1rem 20px;
          min-height: calc(100vh - 80px);
        }

        .hero-title {
          font-size: 1.8rem;
          margin-bottom: 20px;
        }

        .hero-subtitle {
          font-size: 1rem;
        }

        .hero-actions {
          gap: 12px;
          margin-bottom: 24px;
        }

        .stats-grid {
          grid-template-columns: repeat(3, 1fr);
          max-width: 320px;
          gap: 8px;
        }

        .stat-item {
          padding: 10px 8px;
        }

        .stat-number {
          font-size: 1.3rem;
        }

        .stat-label {
          font-size: 0.65rem;
        }
      }
    `,
  ],
  imports: [
    MatButtonModule,
    MatIconModule,
    RouterLink,
    CommonModule,
    TranslatePipe,
  ],
})
export class Home {
  themeService = inject(ThemeService);
  translationService = inject(TranslationService);
}
