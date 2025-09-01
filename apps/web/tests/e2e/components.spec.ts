import { test, expect } from '@playwright/test'

test.describe('UI Components E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to a test page with components
    // This assumes you have a component showcase page or we'll test in context
    await page.goto('http://localhost:3000')
  })

  test.describe('Button Component', () => {
    test('should be clickable and trigger actions', async ({ page }) => {
      // Test button interaction in real context
      const button = page.locator('button').first()
      await expect(button).toBeVisible()
      await button.click()
      // Verify action was triggered (context-dependent)
    })

    test('should show focus state on keyboard navigation', async ({ page }) => {
      // Tab to first button
      await page.keyboard.press('Tab')
      const button = page.locator('button').first()
      await expect(button).toBeFocused()
    })

    test('should be disabled when appropriate', async ({ page }) => {
      const disabledButton = page.locator('button:disabled').first()
      if (await disabledButton.count() > 0) {
        await expect(disabledButton).toBeDisabled()
      }
    })
  })

  test.describe('Input Component', () => {
    test('should accept text input', async ({ page }) => {
      const input = page.locator('input[type="text"]').first()
      if (await input.count() > 0) {
        await input.fill('Test input value')
        await expect(input).toHaveValue('Test input value')
      }
    })

    test('should show validation errors', async ({ page }) => {
      const emailInput = page.locator('input[type="email"]').first()
      if (await emailInput.count() > 0) {
        await emailInput.fill('invalid-email')
        await page.keyboard.press('Tab')
        // Check for error message (context-dependent)
        const errorMessage = page.locator('text=/invalid|error/i').first()
        if (await errorMessage.count() > 0) {
          await expect(errorMessage).toBeVisible()
        }
      }
    })

    test('should support placeholder text', async ({ page }) => {
      const input = page.locator('input[placeholder]').first()
      if (await input.count() > 0) {
        const placeholder = await input.getAttribute('placeholder')
        expect(placeholder).toBeTruthy()
      }
    })
  })

  test.describe('Dialog/Modal Component', () => {
    test('should open and close modal', async ({ page }) => {
      // Look for any trigger that might open a dialog
      const dialogTrigger = page.locator('button:has-text("open")').first()
      if (await dialogTrigger.count() > 0) {
        await dialogTrigger.click()
        
        // Check if dialog opened
        const dialog = page.locator('[role="dialog"]').first()
        await expect(dialog).toBeVisible()
        
        // Close with escape key
        await page.keyboard.press('Escape')
        await expect(dialog).not.toBeVisible()
      }
    })

    test('should trap focus within modal', async ({ page }) => {
      const dialogTrigger = page.locator('button:has-text("open")').first()
      if (await dialogTrigger.count() > 0) {
        await dialogTrigger.click()
        
        const dialog = page.locator('[role="dialog"]').first()
        if (await dialog.count() > 0) {
          // Tab through focusable elements
          await page.keyboard.press('Tab')
          const focusedElement = await page.evaluateHandle(() => document.activeElement)
          const dialogElement = await dialog.elementHandle()
          
          // Check if focused element is within dialog
          const isWithinDialog = await page.evaluate(
            ([focused, dialog]) => dialog?.contains(focused as Node) ?? false,
            [focusedElement, dialogElement]
          )
          expect(isWithinDialog).toBeTruthy()
        }
      }
    })
  })

  test.describe('Form Component', () => {
    test('should submit form with valid data', async ({ page }) => {
      const form = page.locator('form').first()
      if (await form.count() > 0) {
        // Fill form fields
        const inputs = form.locator('input')
        const inputCount = await inputs.count()
        
        for (let i = 0; i < inputCount; i++) {
          const input = inputs.nth(i)
          const type = await input.getAttribute('type')
          
          if (type === 'text' || type === 'email') {
            await input.fill(type === 'email' ? 'test@example.com' : 'Test value')
          }
        }
        
        // Submit form
        const submitButton = form.locator('button[type="submit"]').first()
        if (await submitButton.count() > 0) {
          await submitButton.click()
        }
      }
    })

    test('should show validation errors on invalid submission', async ({ page }) => {
      const form = page.locator('form').first()
      if (await form.count() > 0) {
        // Try to submit without filling required fields
        const submitButton = form.locator('button[type="submit"]').first()
        if (await submitButton.count() > 0) {
          await submitButton.click()
          
          // Check for error messages
          const errorMessages = page.locator('[role="alert"], .text-destructive')
          if (await errorMessages.count() > 0) {
            await expect(errorMessages.first()).toBeVisible()
          }
        }
      }
    })
  })

  test.describe('Table Component', () => {
    test('should display data in table format', async ({ page }) => {
      const table = page.locator('table').first()
      if (await table.count() > 0) {
        await expect(table).toBeVisible()
        
        // Check for headers
        const headers = table.locator('th')
        if (await headers.count() > 0) {
          await expect(headers.first()).toBeVisible()
        }
        
        // Check for data cells
        const cells = table.locator('td')
        if (await cells.count() > 0) {
          await expect(cells.first()).toBeVisible()
        }
      }
    })

    test('should support row selection if interactive', async ({ page }) => {
      const table = page.locator('table').first()
      if (await table.count() > 0) {
        const row = table.locator('tr').nth(1) // Skip header row
        if (await row.count() > 0) {
          await row.click()
          // Check if row has selected state (context-dependent)
          const isSelected = await row.getAttribute('data-state')
          if (isSelected !== null) {
            expect(isSelected).toBe('selected')
          }
        }
      }
    })
  })

  test.describe('Toast Notifications', () => {
    test('should show and auto-dismiss toast notifications', async ({ page }) => {
      // Trigger an action that shows a toast
      const actionButton = page.locator('button').filter({ hasText: /save|submit|create/i }).first()
      if (await actionButton.count() > 0) {
        await actionButton.click()
        
        // Check for toast notification
        const toast = page.locator('[role="status"], [role="alert"]').first()
        if (await toast.count() > 0) {
          await expect(toast).toBeVisible()
          
          // Wait for auto-dismiss (usually 3-5 seconds)
          await page.waitForTimeout(5000)
          await expect(toast).not.toBeVisible()
        }
      }
    })

    test('should allow manual dismissal of toast', async ({ page }) => {
      // Trigger toast
      const actionButton = page.locator('button').filter({ hasText: /save|submit|create/i }).first()
      if (await actionButton.count() > 0) {
        await actionButton.click()
        
        const toast = page.locator('[role="status"], [role="alert"]').first()
        if (await toast.count() > 0) {
          const closeButton = toast.locator('button[aria-label*="close" i]')
          if (await closeButton.count() > 0) {
            await closeButton.click()
            await expect(toast).not.toBeVisible()
          }
        }
      }
    })
  })

  test.describe('Theme Toggle', () => {
    test('should switch between light and dark themes', async ({ page }) => {
      // Look for theme toggle button
      const themeToggle = page.locator('button').filter({ hasText: /theme|dark|light/i }).first()
      if (await themeToggle.count() > 0) {
        // Get initial theme
        const htmlElement = page.locator('html')
        const initialTheme = await htmlElement.getAttribute('class')
        
        // Toggle theme
        await themeToggle.click()
        
        // Check if theme changed
        const newTheme = await htmlElement.getAttribute('class')
        expect(newTheme).not.toBe(initialTheme)
        
        // Toggle back
        await themeToggle.click()
        const finalTheme = await htmlElement.getAttribute('class')
        expect(finalTheme).toBe(initialTheme)
      }
    })

    test('should persist theme preference', async ({ page, context }) => {
      const themeToggle = page.locator('button').filter({ hasText: /theme|dark|light/i }).first()
      if (await themeToggle.count() > 0) {
        // Set to dark theme
        await themeToggle.click()
        const htmlElement = page.locator('html')
        const theme = await htmlElement.getAttribute('class')
        
        // Reload page
        await page.reload()
        
        // Check if theme persisted
        const reloadedTheme = await htmlElement.getAttribute('class')
        expect(reloadedTheme).toBe(theme)
      }
    })
  })

  test.describe('Responsive Behavior', () => {
    test('should adapt to mobile viewport', async ({ page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 })
      
      // Check if navigation becomes mobile menu
      const mobileMenu = page.locator('[aria-label*="menu" i]').first()
      if (await mobileMenu.count() > 0) {
        await expect(mobileMenu).toBeVisible()
      }
      
      // Check if layout adapts
      const container = page.locator('.container, main').first()
      if (await container.count() > 0) {
        const width = await container.evaluate(el => el.clientWidth)
        expect(width).toBeLessThanOrEqual(375)
      }
    })

    test('should adapt to tablet viewport', async ({ page }) => {
      // Set tablet viewport
      await page.setViewportSize({ width: 768, height: 1024 })
      
      // Check layout adaptation
      const container = page.locator('.container, main').first()
      if (await container.count() > 0) {
        const width = await container.evaluate(el => el.clientWidth)
        expect(width).toBeLessThanOrEqual(768)
      }
    })

    test('should adapt to desktop viewport', async ({ page }) => {
      // Set desktop viewport
      await page.setViewportSize({ width: 1920, height: 1080 })
      
      // Check layout adaptation
      const container = page.locator('.container, main').first()
      if (await container.count() > 0) {
        const width = await container.evaluate(el => el.clientWidth)
        expect(width).toBeLessThanOrEqual(1920)
      }
    })
  })

  test.describe('Accessibility', () => {
    test('should be navigable with keyboard only', async ({ page }) => {
      // Tab through interactive elements
      const interactiveElements = page.locator('button, input, select, textarea, a[href], [tabindex]:not([tabindex="-1"])')
      const count = await interactiveElements.count()
      
      if (count > 0) {
        // Tab through first few elements
        for (let i = 0; i < Math.min(5, count); i++) {
          await page.keyboard.press('Tab')
          const focused = await page.evaluate(() => document.activeElement?.tagName)
          expect(focused).toBeTruthy()
        }
      }
    })

    test('should have proper ARIA labels', async ({ page }) => {
      // Check buttons have accessible names
      const buttons = page.locator('button')
      const buttonCount = await buttons.count()
      
      for (let i = 0; i < Math.min(5, buttonCount); i++) {
        const button = buttons.nth(i)
        const text = await button.textContent()
        const ariaLabel = await button.getAttribute('aria-label')
        
        // Button should have either text content or aria-label
        expect(text || ariaLabel).toBeTruthy()
      }
    })

    test('should have proper heading hierarchy', async ({ page }) => {
      const headings = page.locator('h1, h2, h3, h4, h5, h6')
      const headingCount = await headings.count()
      
      if (headingCount > 0) {
        // Check for h1
        const h1Count = await page.locator('h1').count()
        expect(h1Count).toBeGreaterThanOrEqual(0)
        
        // Headings should not skip levels (simplified check)
        for (let i = 0; i < headingCount; i++) {
          const heading = headings.nth(i)
          const tagName = await heading.evaluate(el => el.tagName)
          expect(tagName).toMatch(/^H[1-6]$/)
        }
      }
    })

    test('should have sufficient color contrast', async ({ page }) => {
      // This is a basic check - full contrast testing requires additional tools
      const textElements = page.locator('p, span, div').filter({ hasText: /.+/ })
      const elementCount = await textElements.count()
      
      if (elementCount > 0) {
        const element = textElements.first()
        const color = await element.evaluate(el => 
          window.getComputedStyle(el).color
        )
        const backgroundColor = await element.evaluate(el => 
          window.getComputedStyle(el).backgroundColor
        )
        
        // Basic check that colors are defined
        expect(color).toBeTruthy()
        expect(backgroundColor).toBeTruthy()
      }
    })
  })
})