import { test, expect } from '@playwright/test';

test('TH strip: 18px height', async ({ page }) => {
  await page.goto('http://localhost:3000');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(3000);

  const strip = page.locator('[data-testid="strip-trade-history"]');
  await expect(strip).toBeVisible({ timeout: 10000 });

  const height = await strip.evaluate(el => parseInt(getComputedStyle(el).height));
  expect(height).toBe(18);
});
