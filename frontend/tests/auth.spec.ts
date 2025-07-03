import { test, expect } from '@playwright/test';

test.describe('Authentication Flows', () => {
  test('should allow a user to request a password reset', async ({ page }) => {
    // Mock the API response for password reset
    await page.route('**/api/auth/reset-password', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'Password reset email sent successfully',
        }),
      });
    });

    // Navigate to the forgot password page
    await page.goto('/forgot-password');

    // Wait for the page to load and form to be ready
    await page.waitForSelector('form');
    await page.waitForSelector('#email');

    // Wait for translations to load
    await page.waitForTimeout(1000);

    // Fill in the email address using ID selector
    await page.locator('#email').fill('test-user@example.com');

    // Click the "Reset Password" button using the translated text
    await page.getByRole('button', { name: 'Reset Password' }).click();

    // Assert that the success message is visible
    await expect(page.getByText('Email Sent Successfully!')).toBeVisible();
    await expect(
      page.getByText(
        "If an account with that email exists, you'll receive password reset instructions shortly."
      )
    ).toBeVisible();
  });

  test('should allow a user to create a new account', async ({ page }) => {
    // Generate a unique username and email for each test run
    const randomId = Math.random().toString(36).substring(2, 8);
    const username = `testuser_${randomId}`;
    const email = `test-${username}@example.com`;

    // Mock the API response for registration
    await page.route('**/api/auth/register', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          details: {
            user_id: 'test-user-id-123',
          },
        }),
      });
    });

    // Navigate to the register page
    await page.goto('/register');

    // Wait for the page to load and form to be ready
    await page.waitForSelector('form');
    await page.waitForSelector('#username');
    await page.waitForSelector('#email');
    await page.waitForSelector('#password');
    await page.waitForSelector('#confirmPassword');

    // Wait for translations to load
    await page.waitForTimeout(1000);

    // Fill in the registration form with unique data using ID selectors
    await page.locator('#username').fill(username);
    await page.locator('#email').fill(email);
    await page.locator('#password').fill('Password123!');
    await page.locator('#confirmPassword').fill('Password123!');

    // Click the "Create Account" button using translated text
    await page.getByRole('button', { name: 'Create Account' }).click();

    // Assert that the user is redirected to the verify page, ignoring query parameters
    await expect(page).toHaveURL(/\/verify/);
    await expect(
      page.getByText(`We've sent a verification code to ${email}`)
    ).toBeVisible();
  });

  test('should show validation error for short username', async ({ page }) => {
    await page.goto('/register');

    // Wait for the page to load
    await page.waitForSelector('form');
    await page.waitForSelector('#username');

    const usernameInput = page.locator('#username');
    await usernameInput.fill('us');
    await usernameInput.blur();
    await expect(page.getByText('Must be at least 3 characters')).toBeVisible();
  });

  test('should show validation error for invalid email', async ({ page }) => {
    await page.goto('/register');

    // Wait for the page to load
    await page.waitForSelector('form');
    await page.waitForSelector('#email');

    const emailInput = page.locator('#email');
    await emailInput.fill('invalid-email');
    await emailInput.blur();
    await expect(
      page.getByText('Please enter a valid email address')
    ).toBeVisible();
  });

  test('should show validation error for short password', async ({ page }) => {
    await page.goto('/register');

    // Wait for the page to load
    await page.waitForSelector('form');
    await page.waitForSelector('#password');

    const passwordInput = page.locator('#password');
    await passwordInput.fill('pass');
    await passwordInput.blur();
    await expect(page.getByText('Must be at least 8 characters')).toBeVisible();
  });
});

test.describe('Login Flow', () => {
  test('should show validation error for invalid email on login', async ({
    page,
  }) => {
    await page.goto('/login');

    // Wait for the page to load
    await page.waitForSelector('form');
    await page.waitForSelector('#email');

    // Wait for translations to load
    await page.waitForTimeout(1000);

    const emailInput = page.locator('#email');
    await emailInput.fill('not-an-email');
    await emailInput.blur();
    await expect(
      page.getByText('Please enter a valid email address')
    ).toBeVisible();
  });

  test('should show validation error for short password on login', async ({
    page,
  }) => {
    await page.goto('/login');

    // Wait for the page to load
    await page.waitForSelector('form');
    await page.waitForSelector('#password');

    // Wait for translations to load
    await page.waitForTimeout(1000);

    const passwordInput = page.locator('#password');
    await passwordInput.fill('short');
    await passwordInput.blur();
    await expect(page.getByText('Must be at least 8 characters')).toBeVisible();
  });

  test('should show error for invalid credentials', async ({ page }) => {
    // Mock the API response for invalid login
    await page.route('**/api/auth/login', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          // Missing required fields (token, details.user) will cause login to return false
        }),
      });
    });

    await page.goto('/login');

    // Wait for the page to load
    await page.waitForSelector('form');
    await page.waitForSelector('#email');
    await page.waitForSelector('#password');

    // Wait for translations to load
    await page.waitForTimeout(1000);

    await page.locator('#email').fill('wrong@example.com');
    await page.locator('#password').fill('wrongpassword');
    await page.getByRole('button', { name: 'Sign In' }).click();

    await expect(
      page
        .locator('.error-snackbar')
        .getByText('Invalid credentials. Please try again.')
    ).toBeVisible();
  });
});
