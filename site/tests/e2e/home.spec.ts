import { test, expect } from '@playwright/test';

test.describe('OpenRoleRadar site', () => {
  test('home page loads with search UI', async ({ page }) => {
    await page.goto('./', { waitUntil: 'networkidle' });
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await expect(page.locator('#search-query')).toBeVisible({ timeout: 15_000 });
  });

  test('filter combination updates URL', async ({ page }) => {
    await page.goto('./', { waitUntil: 'networkidle' });
    await page.locator('#search-query').waitFor({ timeout: 15_000 });
    const internship = page.getByLabel(/internship/i).first();
    if (await internship.isVisible()) {
      await internship.check();
      await page.waitForTimeout(300);
      expect(page.url()).toMatch(/careerLevels|level/i);
    }
  });

  test('dark theme toggle works', async ({ page }) => {
    await page.goto('./', { waitUntil: 'networkidle' });
    const themeButton = page.getByRole('button', { name: /theme/i });
    if (await themeButton.isVisible()) {
      await themeButton.click();
      const theme = await page.locator('html').getAttribute('data-theme');
      expect(theme).toBeTruthy();
    }
  });

  test('status page loads', async ({ page }) => {
    await page.goto('status/', { waitUntil: 'networkidle' });
    await expect(page.locator('h1')).toContainText(/platform status/i);
    await expect(page.getByText(/manifest version/i)).toBeVisible();
  });

  test('mobile layout is usable', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('./', { waitUntil: 'networkidle' });
    await expect(page.getByRole('main')).toBeVisible();
  });
});
