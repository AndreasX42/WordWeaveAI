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

    // Fill in the email address
    await page.getByLabel('Email Address').fill('test-user@example.com');

    // Click the "Reset Password" button
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

    // Fill in the registration form with unique data
    await page.getByLabel('Username').fill(username);
    await page.getByLabel('Email address').fill(email);
    await page
      .getByRole('textbox', { name: 'Password', exact: true })
      .fill('Password123!');
    await page
      .getByRole('textbox', { name: 'Confirm password', exact: true })
      .fill('Password123!');

    // Click the "Create Account" button
    await page.getByRole('button', { name: 'Create Account' }).click();

    // Assert that the user is redirected to the verify page, ignoring query parameters
    await expect(page).toHaveURL(/\/verify/);
    await expect(
      page.getByText(`We've sent a verification code to ${email}`)
    ).toBeVisible();
  });

  test('should show validation error for short username', async ({ page }) => {
    await page.goto('/register');
    const usernameInput = page.getByLabel('Username');
    await usernameInput.fill('us');
    await usernameInput.blur();
    await expect(page.getByText('Must be at least 3 characters')).toBeVisible();
  });

  test('should show validation error for invalid email', async ({ page }) => {
    await page.goto('/register');
    const emailInput = page.getByLabel('Email address');
    await emailInput.fill('invalid-email');
    await emailInput.blur();
    await expect(
      page.getByText('Please enter a valid email address')
    ).toBeVisible();
  });

  test('should show validation error for short password', async ({ page }) => {
    await page.goto('/register');
    const passwordInput = page.getByRole('textbox', {
      name: 'Password',
      exact: true,
    });
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
    const emailInput = page.getByLabel('Email Address');
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
    const passwordInput = page.getByRole('textbox', {
      name: 'Password',
      exact: true,
    });
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
    await page.getByLabel('Email Address').fill('wrong@example.com');
    await page
      .getByRole('textbox', { name: 'Password', exact: true })
      .fill('wrongpassword');
    await page.getByRole('button', { name: 'Sign In' }).click();

    await expect(
      page
        .locator('.error-snackbar')
        .getByText('Invalid credentials. Please try again.')
    ).toBeVisible();
  });
});
