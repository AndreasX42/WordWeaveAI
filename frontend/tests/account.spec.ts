import { test, expect } from '@playwright/test';

test.describe('Update Account Flow', () => {
  // Set up a logged-in state before each test
  test.beforeEach(async ({ page }) => {
    // Mock API calls that the profile page might make
    await page.route('**/api/auth/refresh', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ token: 'mock-auth-token' }),
      });
    });

    await page.addInitScript(() => {
      const mockUser = {
        id: 'user-123',
        username: 'TestUser',
        email: 'test@example.com',
        confirmedEmail: true,
        profilePicture: '',
        role: 'user',
      };
      localStorage.setItem('auth_user', JSON.stringify(mockUser));
      localStorage.setItem('auth_token', 'mock-auth-token');
    });
    await page.goto('/profile');
  });

  test('should allow a user to successfully update their account', async ({
    page,
  }) => {
    // Mock the successful API response for the update
    await page.route('**/api/users/update', async (route) => {
      await route.fulfill({ status: 200 });
    });

    // Open the update dialog
    await page.getByRole('button', { name: /update account/i }).click();

    // Get a locator for the dialog to scope actions
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();

    // Fill in the new details within the dialog
    await dialog.locator('#update-username').fill('UpdatedUser');
    await dialog
      .getByRole('button', { name: /update account/i, exact: true })
      .click();

    // The success message appears in a snackbar with a specific class
    await expect(
      page
        .locator('.success-snackbar')
        .getByText('Account updated successfully!')
    ).toBeVisible();
    // The dialog should close on success
    await expect(dialog).not.toBeVisible();
  });

  test('should show validation error for username that already exists', async ({
    page,
  }) => {
    // Mock the API to return a "username already exists" error
    await page.route('**/api/users/update', async (route) => {
      await route.fulfill({
        status: 400,
        body: JSON.stringify({
          details: { error: 'username already exists' },
        }),
      });
    });

    await page.getByRole('button', { name: /update account/i }).click();

    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();

    await dialog.locator('#update-username').fill('existingUser');
    await dialog
      .getByRole('button', { name: /update account/i, exact: true })
      .click();

    // The error message should appear within the dialog
    await expect(
      dialog.getByText('This username is already taken')
    ).toBeVisible();
  });

  test('should show validation error for email that already exists', async ({
    page,
  }) => {
    // Mock the API to return an "email already exists" error
    await page.route('**/api/users/update', async (route) => {
      await route.fulfill({
        status: 400,
        body: JSON.stringify({
          details: { error: 'email already exists' },
        }),
      });
    });

    await page.getByRole('button', { name: /update account/i }).click();

    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();

    await dialog.locator('#update-email').fill('existing@example.com');
    await dialog
      .getByRole('button', { name: /update account/i, exact: true })
      .click();

    // The error message should appear within the dialog
    await expect(
      dialog.getByText('This email is already registered')
    ).toBeVisible();
  });

  // Frontend-only validation tests (no API mock needed)
  test('should show validation error for short username', async ({ page }) => {
    await page.getByRole('button', { name: /update account/i }).click();

    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();

    const usernameInput = dialog.locator('#update-username');
    await usernameInput.fill('a');
    await usernameInput.blur();

    await expect(
      dialog.getByText('Must be at least 3 characters')
    ).toBeVisible();
  });

  test('should show validation error for invalid email', async ({ page }) => {
    await page.getByRole('button', { name: /update account/i }).click();

    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();

    const emailInput = dialog.locator('#update-email');
    await emailInput.fill('invalid-email');
    await emailInput.blur();

    await expect(
      dialog.getByText('Please enter a valid email address')
    ).toBeVisible();
  });

  test('should show validation error for short password', async ({ page }) => {
    await page.getByRole('button', { name: /update account/i }).click();

    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();

    const passwordInput = dialog.locator('#update-password');
    await passwordInput.fill('123');
    await passwordInput.blur();

    await expect(
      dialog.getByText('Must be at least 8 characters')
    ).toBeVisible();
  });

  test('should have update button disabled when no changes are made', async ({
    page,
  }) => {
    await page.getByRole('button', { name: /update account/i }).click();

    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();

    const updateButton = dialog.getByRole('button', {
      name: /update account/i,
      exact: true,
    });

    // 1. Assert button is disabled initially
    await expect(updateButton).toBeDisabled();

    // 2. Change username and assert button is enabled
    const usernameInput = dialog.locator('#update-username');
    await usernameInput.fill('NewUsername');
    await expect(updateButton).toBeEnabled();

    // 3. Change username back to original and assert button is disabled again
    await usernameInput.fill('TestUser');
    await expect(updateButton).toBeDisabled();

    // 4. Change email and assert button is enabled
    const emailInput = dialog.locator('#update-email');
    await emailInput.fill('new@example.com');
    await expect(updateButton).toBeEnabled();

    // 5. Change email back to original and assert button is disabled again
    await emailInput.fill('test@example.com');
    await expect(updateButton).toBeDisabled();
  });
});
