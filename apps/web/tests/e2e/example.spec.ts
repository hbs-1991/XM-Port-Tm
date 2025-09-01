import { test, expect } from '@playwright/test';

test('homepage loads', async ({ page }) => {
  await page.goto('/');
  
  // Expect page title to contain "XM-Port" 
  await expect(page).toHaveTitle(/XM-Port/);
});

test('navigation works', async ({ page }) => {
  await page.goto('/');
  
  // Example: Click on a navigation link (when implemented)
  // await page.click('text=Dashboard');
  // await expect(page).toHaveURL('/dashboard');
  
  // For now, just verify the page loads
  await expect(page.locator('body')).toBeVisible();
});

test('responsive design', async ({ page }) => {
  // Test mobile viewport
  await page.setViewportSize({ width: 375, height: 667 });
  await page.goto('/');
  
  await expect(page.locator('body')).toBeVisible();
  
  // Test desktop viewport
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto('/');
  
  await expect(page.locator('body')).toBeVisible();
});