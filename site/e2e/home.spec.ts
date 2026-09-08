import { test, expect } from '@playwright/test';

test('homepage loads with branding and search UI', async ({ page }) => {
  await page.goto('./');
  await expect(page.getByRole('heading', { name: /find roles that move with you/i })).toBeVisible();
  await expect(page.getByLabel('Job filters')).toBeVisible();
  await expect(page.getByLabel('Platform statistics')).toBeVisible();
});

test('status page shows manifest info', async ({ page }) => {
  await page.goto('./status');
  await expect(page.getByRole('heading', { name: /platform status/i })).toBeVisible();
  await expect(page.getByText('Manifest version')).toBeVisible();
});
