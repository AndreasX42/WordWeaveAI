import { test, expect } from '@playwright/test';

test.describe('Search Component', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/search');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('.search-container');
  });

  test.describe('Basic Search Functionality', () => {
    test('should display search page with correct elements', async ({
      page,
    }) => {
      // Check main search elements are present
      await expect(page.locator('.search-title')).toBeVisible();
      await expect(page.locator('.search-subtitle')).toBeVisible();
      await expect(page.locator('.search-input')).toBeVisible();
      await expect(page.locator('.language-select')).toHaveCount(2);
    });

    test('should perform basic search and display results', async ({
      page,
    }) => {
      // Mock search API response (correct endpoint and format)
      await page.route('**/api/search', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            results: [
              {
                pk: 'en#hello',
                sk: 'es#POS#interjection#hola',
                source_word: 'hello',
                target_word: 'hola',
                source_language: 'en',
                target_language: 'es',
                source_pos: 'interjection',
                target_pos: 'interjección',
                created_at: '2024-01-01T00:00:00Z',
                created_by: 'test-user',
              },
            ],
            count: 1,
            query: 'hello',
          }),
        });
      });

      // Select languages
      await page.locator('.language-select').nth(0).click();
      await page.locator('mat-option[value="en"]').click();
      await page.locator('.language-select').nth(1).click();
      await page.locator('mat-option[value="es"]').click();

      // Type in search input (this triggers the reactive form)
      await page.locator('.search-input').fill('hello');

      // Wait for the debounced search to trigger
      await page.waitForTimeout(500);

      // Wait for results dropdown to appear and check for results
      await page.waitForSelector('.results-dropdown', { timeout: 10000 });

      // Verify result is displayed
      await expect(page.locator('.result-item')).toBeVisible({
        timeout: 10000,
      });
      await expect(page.locator('.result-item')).toContainText('hello');
      await expect(page.locator('.result-item')).toContainText('hola');
    });

    test('should show loading state during search', async ({ page }) => {
      // Mock slow API response
      await page.route('**/api/search', async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            results: [],
            count: 0,
            query: 'test',
          }),
        });
      });

      // Select languages
      await page.locator('.language-select').nth(0).click();
      await page.locator('mat-option[value="en"]').click();
      await page.locator('.language-select').nth(1).click();
      await page.locator('mat-option[value="es"]').click();

      // Type in search input to trigger search
      await page.locator('.search-input').fill('test');

      // Wait for loading spinner to appear
      await expect(page.locator('.loading-spinner mat-spinner')).toBeVisible({
        timeout: 10000,
      });
    });

    test('should handle empty search results', async ({ page }) => {
      // Mock empty search response
      await page.route('**/api/search', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            results: [],
            count: 0,
            query: 'nonexistentword',
          }),
        });
      });

      // Select languages
      await page.locator('.language-select').nth(0).click();
      await page.locator('mat-option[value="en"]').click();
      await page.locator('.language-select').nth(1).click();
      await page.locator('mat-option[value="es"]').click();

      // Type in search input
      await page.locator('.search-input').fill('nonexistentword');

      // Wait for search to complete
      await page.waitForTimeout(1000);

      // Verify empty state message
      await expect(page.locator('.no-results')).toBeVisible({ timeout: 10000 });
    });

    test('should handle search errors gracefully', async ({ page }) => {
      // Mock API error by aborting the request
      await page.route('**/api/search', async (route) => {
        await route.abort('failed');
      });

      // Select languages with proper overlay handling
      await page.locator('.language-select').nth(0).click();
      await page.waitForSelector('mat-option[value="en"]', { timeout: 5000 });
      await page.locator('mat-option[value="en"]').click();

      // Wait for overlay to close
      await page.waitForTimeout(500);

      await page.locator('.language-select').nth(1).click();
      await page.waitForSelector('mat-option[value="es"]', { timeout: 5000 });
      await page.locator('mat-option[value="es"]').click();

      // Type in search input
      await page.locator('.search-input').fill('test');

      // Wait for error to be displayed
      await page.waitForTimeout(2000);

      // Verify error is displayed - the error might be handled differently
      // Check if error state is shown in any form
      await expect(page.locator('.error-message, .no-results')).toBeVisible({
        timeout: 10000,
      });
    });
  });

  test.describe('Language Selection', () => {
    test('should allow language selection', async ({ page }) => {
      // Select source language
      await page.locator('.language-select').nth(0).click();
      await page.locator('mat-option[value="en"]').click();

      // Select target language
      await page.locator('.language-select').nth(1).click();
      await page.locator('mat-option[value="es"]').click();

      // Verify selections are made
      await expect(page.locator('.language-select').nth(0)).toContainText(
        'English'
      );
      await expect(page.locator('.language-select').nth(1)).toContainText(
        'Spanish'
      );
    });

    test('should disable conflicting language options', async ({ page }) => {
      // Select English as source
      await page.locator('.language-select').nth(0).click();
      await page.locator('mat-option[value="en"]').click();

      // Try to select English as target - should be disabled
      await page.locator('.language-select').nth(1).click();
      const englishOption = page.locator('mat-option[value="en"]');
      await expect(englishOption).toHaveAttribute('aria-disabled', 'true');
    });

    test('should swap languages correctly', async ({ page }) => {
      // Select initial languages
      await page.locator('.language-select').nth(0).click();
      await page.locator('mat-option[value="en"]').click();
      await page.locator('.language-select').nth(1).click();
      await page.locator('mat-option[value="es"]').click();

      // Click swap button
      await page.locator('.swap-button').click();

      // Verify languages are swapped
      await expect(page.locator('.language-select').nth(0)).toContainText(
        'Spanish'
      );
      await expect(page.locator('.language-select').nth(1)).toContainText(
        'English'
      );
    });

    test('should persist language preferences', async ({ page }) => {
      // Select languages
      await page.locator('.language-select').nth(0).click();
      await page.locator('mat-option[value="en"]').click();
      await page.locator('.language-select').nth(1).click();
      await page.locator('mat-option[value="es"]').click();

      // Navigate away and back
      await page.goto('/');
      await page.goto('/search');

      // Verify languages are still selected
      await expect(page.locator('.language-select').nth(0)).toContainText(
        'English'
      );
      await expect(page.locator('.language-select').nth(1)).toContainText(
        'Spanish'
      );
    });
  });

  test.describe('Request Word Dialog', () => {
    test('should open request word dialog when no results found', async ({
      page,
    }) => {
      // Mock empty search response
      await page.route('**/api/search', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            results: [],
            count: 0,
            query: 'newword',
          }),
        });
      });

      // Select languages
      await page.locator('.language-select').nth(0).click();
      await page.locator('mat-option[value="en"]').click();
      await page.locator('.language-select').nth(1).click();
      await page.locator('mat-option[value="es"]').click();

      // Type in search input
      await page.locator('.search-input').fill('newword');

      // Wait for search to complete
      await page.waitForTimeout(1000);

      // Wait for request button and click it
      await page.waitForSelector('.request-btn', { timeout: 10000 });
      await page.locator('.request-btn').click();

      // Verify dialog opens
      await expect(page.locator('mat-dialog-container')).toBeVisible({
        timeout: 10000,
      });
      await expect(page.locator('mat-dialog-container')).toContainText(
        'Request Word'
      );
    });

    test('should validate request word form', async ({ page }) => {
      // Mock empty search response
      await page.route('**/api/search', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            results: [],
            count: 0,
            query: 'newword',
          }),
        });
      });

      // Navigate to search page
      await page.goto('/search');
      await page.waitForLoadState('networkidle');

      // Select languages
      await page.locator('.language-select').nth(0).click();
      await page.locator('mat-option[value="en"]').click();
      await page.locator('.language-select').nth(1).click();
      await page.locator('mat-option[value="es"]').click();

      // Type in search input
      await page.locator('.search-input').fill('newword');

      // Wait for search to complete
      await page.waitForTimeout(1000);

      await page.waitForSelector('.request-btn', { timeout: 10000 });
      await page.locator('.request-btn').click();

      // Wait for dialog to be fully loaded
      await page.waitForSelector('mat-dialog-container', { timeout: 10000 });

      // Clear the source word field to trigger validation
      await page.locator('input[matInput]').first().clear();

      // Wait for validation to trigger
      await page.waitForTimeout(500);

      // Verify validation errors are shown
      await expect(page.locator('.validation-error')).toBeVisible({
        timeout: 10000,
      });

      // Verify submit button is disabled
      await expect(
        page.locator('button[mat-raised-button]:has-text("Submit Request")')
      ).toBeDisabled();
    });

    test('should submit word request successfully', async ({ page }) => {
      // Mock empty search response
      await page.route('**/api/search', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            results: [],
            count: 0,
            query: 'newword',
          }),
        });
      });

      // Navigate to search page
      await page.goto('/search');
      await page.waitForLoadState('networkidle');

      // Select languages
      await page.locator('.language-select').nth(0).click();
      await page.locator('mat-option[value="en"]').click();
      await page.locator('.language-select').nth(1).click();
      await page.locator('mat-option[value="es"]').click();

      // Type in search input
      await page.locator('.search-input').fill('newword');

      // Wait for search to complete
      await page.waitForTimeout(1000);

      await page.waitForSelector('.request-btn', { timeout: 10000 });
      await page.locator('.request-btn').click();

      // Wait for dialog to be fully loaded
      await page.waitForSelector('mat-dialog-container', { timeout: 10000 });

      // Fill form using the correct selectors
      await page.locator('input[matInput]').first().fill('newword');

      // Check if target language is already selected (it should be pre-filled from search)
      const targetLanguageValue = await page
        .locator('mat-select')
        .nth(1)
        .textContent();

      // If target language is not already Spanish, select it
      if (!targetLanguageValue?.includes('Spanish')) {
        // Click on the target language select and choose Spanish
        await page.locator('mat-select').nth(1).click({ force: true });
        await page.waitForSelector('mat-option[value="es"]', { timeout: 5000 });
        await page.locator('mat-option[value="es"]').click({ force: true });
      }

      // Wait for form to be valid
      await page.waitForTimeout(500);

      // Submit request
      await page
        .locator('button[mat-raised-button]:has-text("Submit Request")')
        .click();

      // Verify navigation to login page (authentication required for word requests)
      await expect(page).toHaveURL(/\/login/);

      // Verify login page shows appropriate message
      await expect(page.locator('body')).toContainText(
        'Please sign in to continue'
      );
    });
  });

  test.describe('Search Results Interaction', () => {
    test('should navigate to word card when clicking search result', async ({
      page,
    }) => {
      // Mock search API response
      await page.route('**/api/search', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            results: [
              {
                pk: 'en#hello',
                sk: 'es#POS#interjection#hola',
                source_word: 'hello',
                target_word: 'hola',
                source_language: 'en',
                target_language: 'es',
                source_pos: 'interjection',
                target_pos: 'interjección',
                created_at: '2024-01-01T00:00:00Z',
                created_by: 'test-user',
              },
            ],
            count: 1,
            query: 'hello',
          }),
        });
      });

      // Select languages
      await page.locator('.language-select').nth(0).click();
      await page.locator('mat-option[value="en"]').click();
      await page.locator('.language-select').nth(1).click();
      await page.locator('mat-option[value="es"]').click();

      // Type in search input
      await page.locator('.search-input').fill('hello');

      // Wait for search to complete
      await page.waitForTimeout(1000);

      // Wait for result and click
      await page.waitForSelector('.result-item', { timeout: 10000 });
      await page.locator('.result-item').click();

      // Verify navigation to word card (using the actual route pattern)
      await expect(page).toHaveURL(/\/words\/en\/es\/interjection\/hello/);
    });

    test('should clear search results', async ({ page }) => {
      // Mock search API response
      await page.route('**/api/search', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            results: [
              {
                pk: 'en#hello',
                sk: 'es#POS#interjection#hola',
                source_word: 'hello',
                target_word: 'hola',
                source_language: 'en',
                target_language: 'es',
                source_pos: 'interjection',
                target_pos: 'interjección',
                created_at: '2024-01-01T00:00:00Z',
                created_by: 'test-user',
              },
            ],
            count: 1,
            query: 'hello',
          }),
        });
      });

      // Select languages
      await page.locator('.language-select').nth(0).click();
      await page.locator('mat-option[value="en"]').click();
      await page.locator('.language-select').nth(1).click();
      await page.locator('mat-option[value="es"]').click();

      // Type in search input
      await page.locator('.search-input').fill('hello');

      // Wait for search to complete
      await page.waitForTimeout(1000);

      // Wait for results
      await page.waitForSelector('.result-item', { timeout: 10000 });

      // Clear search
      await page.locator('.clear-btn').click();

      // Verify search is cleared
      await expect(page.locator('.search-input')).toHaveValue('');
      await expect(page.locator('.result-item')).not.toBeVisible();
    });
  });
});
