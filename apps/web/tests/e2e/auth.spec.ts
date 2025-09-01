/**
 * E2E tests for authentication flows
 */
import { test, expect } from '@playwright/test'

test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    // Mock API responses for testing
    await page.route('**/api/v1/auth/register', async (route) => {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          user: {
            id: '123e4567-e89b-12d3-a456-426614174000',
            email: 'test@example.com',
            first_name: 'John',
            last_name: 'Doe',
            role: 'USER',
            is_active: true
          },
          tokens: {
            access_token: 'mock_access_token',
            refresh_token: 'mock_refresh_token',
            token_type: 'bearer',
            expires_in: 900
          }
        })
      })
    })

    await page.route('**/api/v1/auth/login', async (route) => {
      const requestBody = await route.request().postDataJSON()
      
      if (requestBody.email === 'test@example.com' && requestBody.password === 'SecurePass123!') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            user: {
              id: '123e4567-e89b-12d3-a456-426614174000',
              email: 'test@example.com',
              first_name: 'John',
              last_name: 'Doe',
              role: 'USER',
              is_active: true
            },
            tokens: {
              access_token: 'mock_access_token',
              refresh_token: 'mock_refresh_token',
              token_type: 'bearer',
              expires_in: 900
            }
          })
        })
      } else {
        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({
            detail: 'Invalid email or password'
          })
        })
      }
    })
  })

  test('user can register with valid information', async ({ page }) => {
    await page.goto('/auth/register')

    // Fill registration form
    await page.fill('input[name="firstName"]', 'John')
    await page.fill('input[name="lastName"]', 'Doe')
    await page.fill('input[name="email"]', 'test@example.com')
    await page.fill('input[name="password"]', 'SecurePass123!')
    await page.fill('input[name="confirmPassword"]', 'SecurePass123!')

    // Submit form
    await page.click('button[type="submit"]')

    // Should redirect to dashboard (mocked)
    await expect(page).toHaveURL(/dashboard/)
  })

  test('user can login with valid credentials', async ({ page }) => {
    await page.goto('/auth/login')

    // Fill login form
    await page.fill('input[name="email"]', 'test@example.com')
    await page.fill('input[name="password"]', 'SecurePass123!')

    // Submit form
    await page.click('button[type="submit"]')

    // Should redirect to dashboard (mocked)
    await expect(page).toHaveURL(/dashboard/)
  })

  test('login shows error with invalid credentials', async ({ page }) => {
    await page.goto('/auth/login')

    // Fill login form with invalid credentials
    await page.fill('input[name="email"]', 'test@example.com')
    await page.fill('input[name="password"]', 'wrongpassword')

    // Submit form
    await page.click('button[type="submit"]')

    // Should show error message
    await expect(page.locator('text=Invalid email or password')).toBeVisible()
  })

  test('registration form validates password requirements', async ({ page }) => {
    await page.goto('/auth/register')

    // Fill form with weak password
    await page.fill('input[name="firstName"]', 'John')
    await page.fill('input[name="lastName"]', 'Doe')
    await page.fill('input[name="email"]', 'test@example.com')
    await page.fill('input[name="password"]', 'weak')

    // Should show password requirements
    await expect(page.locator('text=Password must contain:')).toBeVisible()
    await expect(page.locator('text=At least 8 characters')).toBeVisible()

    // Submit button should be disabled
    await expect(page.locator('button[type="submit"]')).toBeDisabled()
  })

  test('registration form validates password confirmation', async ({ page }) => {
    await page.goto('/auth/register')

    // Fill form with mismatched passwords
    await page.fill('input[name="password"]', 'SecurePass123!')
    await page.fill('input[name="confirmPassword"]', 'DifferentPass123!')

    // Should show mismatch error
    await expect(page.locator('text=Passwords do not match')).toBeVisible()

    // Submit button should be disabled
    await expect(page.locator('button[type="submit"]')).toBeDisabled()
  })

  test('protected routes redirect to login when not authenticated', async ({ page }) => {
    // Try to access dashboard without authentication
    await page.goto('/dashboard')

    // Should redirect to login page
    await expect(page).toHaveURL(/auth\/login/)
  })

  test('admin routes require admin role', async ({ page }) => {
    // Mock non-admin user session
    await page.addInitScript(() => {
      window.__NEXT_DATA__ = {
        props: {
          session: {
            user: {
              id: '123e4567-e89b-12d3-a456-426614174000',
              email: 'user@example.com',
              role: 'USER'
            }
          }
        }
      }
    })

    // Try to access admin area
    await page.goto('/admin')

    // Should redirect to unauthorized page
    await expect(page).toHaveURL(/unauthorized/)
  })

  test('user can logout successfully', async ({ page }) => {
    // Mock authenticated session
    await page.addInitScript(() => {
      window.__NEXT_DATA__ = {
        props: {
          session: {
            user: {
              id: '123e4567-e89b-12d3-a456-426614174000',
              email: 'test@example.com',
              role: 'USER'
            }
          }
        }
      }
    })

    await page.goto('/dashboard')

    // Find and click logout button (when implemented)
    // This is a placeholder - actual logout UI will be added later
    await page.evaluate(() => {
      // Simulate logout action
      window.dispatchEvent(new CustomEvent('auth:logout'))
    })

    // Should redirect to login page
    await expect(page).toHaveURL(/auth\/login/)
  })
})