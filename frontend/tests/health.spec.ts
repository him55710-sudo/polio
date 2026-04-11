import { test, expect } from '@playwright/test';

test('has title', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/Uni Folia|UniFoli/i);
});

test('get started link', async ({ page }) => {
  await page.goto('/');
  // This is a sample check, replace with your landing page element
  // await page.getByRole('button', { name: 'Get Started' }).click();
});
