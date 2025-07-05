import { test, expect } from '@playwright/test';

const languages = [
  {
    code: 'en',
    name: 'English',
    flag: '🇺🇸',
    hero: 'Build your vocabulary with',
  },
  {
    code: 'de',
    name: 'Deutsch',
    flag: '🇩🇪',
    hero: 'Erweitere deinen Wortschatz mit',
  },
  {
    code: 'es',
    name: 'Español',
    flag: '🇪🇸',
    hero: 'Construye tu vocabulario con',
  },
];

async function switchLanguage(page, languageName) {
  await page.click('.user-button');
  await page.click('button:has-text("Language")');
  await page.click(`button:has-text("${languageName}")`);
  await page.waitForTimeout(300);
}

test.describe('i18n Home Page Language Switch', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('h1.hero-title');
  });

  for (const lang of languages) {
    test(`switching to ${lang.name} updates hero title`, async ({ page }) => {
      await switchLanguage(page, lang.name);
      await expect(page.locator('h1.hero-title')).toContainText(lang.hero);
    });
  }

  test('switching languages updates hero title each time', async ({ page }) => {
    for (const lang of languages) {
      await switchLanguage(page, lang.name);
      await expect(page.locator('h1.hero-title')).toContainText(lang.hero);
    }
  });

  test('switching to German updates stats labels', async ({ page }) => {
    await switchLanguage(page, 'Deutsch');
    await expect(page.locator('.stat-label').nth(0)).toContainText(
      'Wörter erstellt'
    );
    await expect(page.locator('.stat-label').nth(1)).toContainText(
      'Öffentliche Listen'
    );
    await expect(page.locator('.stat-label').nth(2)).toContainText(
      'Aktive Nutzer'
    );
  });

  test('switching to Spanish updates stats labels', async ({ page }) => {
    await switchLanguage(page, 'Español');
    await expect(page.locator('.stat-label').nth(0)).toContainText(
      'Palabras creadas'
    );
    await expect(page.locator('.stat-label').nth(1)).toContainText(
      'Listas públicas'
    );
    await expect(page.locator('.stat-label').nth(2)).toContainText(
      'Usuarios activos'
    );
  });

  test('switching to English updates stats labels', async ({ page }) => {
    await switchLanguage(page, 'English');
    await expect(page.locator('.stat-label').nth(0)).toContainText(
      'Words Created'
    );
    await expect(page.locator('.stat-label').nth(1)).toContainText(
      'Public Lists'
    );
    await expect(page.locator('.stat-label').nth(2)).toContainText(
      'Active Users'
    );
  });

  test('switching to German updates CTA button', async ({ page }) => {
    await switchLanguage(page, 'Deutsch');
    await expect(page.locator('.cta-button')).toContainText('Jetzt loslegen');
  });

  test('switching to Spanish updates CTA button', async ({ page }) => {
    await switchLanguage(page, 'Español');
    await expect(page.locator('.cta-button')).toContainText('Empieza ahora');
  });

  test('switching to English updates CTA button', async ({ page }) => {
    await switchLanguage(page, 'English');
    await expect(page.locator('.cta-button')).toContainText('Start building');
  });
});
