import { Component } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-home',
  standalone: true,
  template: `
    <div class="home-container">
      <div class="welcome-section">
        <h1>Welcome to WordWeave</h1>
        <p>Your creative writing companion</p>
        <div class="action-buttons">
          <button mat-raised-button color="primary" routerLink="/profile">
            Get Started
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [
    `
      .home-container {
        display: flex;
        align-items: flex-start;
        justify-content: center;
        min-height: calc(100vh - 64px);
        padding: 80px 24px 24px;
        text-align: center;
      }

      .welcome-section {
        max-width: 600px;
      }

      h1 {
        font-size: 3rem;
        font-weight: 700;
        margin-bottom: 16px;
        color: var(--text-primary);
      }

      p {
        font-size: 1.2rem;
        color: var(--text-secondary);
        margin-bottom: 32px;
      }

      .action-buttons {
        display: flex;
        gap: 16px;
        justify-content: center;
      }

      button {
        padding: 12px 32px;
        font-size: 16px;
      }

      /* Mobile-first responsive design */
      @media (max-width: 599px) {
        .home-container {
          padding: 80px 16px 24px !important;
          min-height: calc(100vh - 56px) !important;
        }

        .welcome-section {
          max-width: 100% !important;
        }

        h1 {
          font-size: 2rem !important;
          margin-bottom: 12px !important;
        }

        p {
          font-size: 1rem !important;
          margin-bottom: 24px !important;
          line-height: 1.5 !important;
        }

        .action-buttons {
          flex-direction: column !important;
          align-items: center !important;
          gap: 12px !important;

          button {
            width: 100% !important;
            max-width: 280px !important;
            padding: 14px 32px !important;
            font-size: 16px !important;
            height: 48px !important;
          }
        }
      }
    `,
  ],
  imports: [MatButtonModule, RouterLink],
})
export class Home {}
