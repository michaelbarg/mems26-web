import { test, expect } from '@playwright/test';

test('C10: X-axis drag region exists and is interactive', async ({ page }) => {
  await page.goto('http://localhost:3000');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(5000);

  const xAxis = page.locator('[data-testid="chart-xaxis-region"]');
  await expect(xAxis).toBeVisible({ timeout: 10000 });

  const cursor = await xAxis.getAttribute('cursor');
  expect(cursor).toBe('ew-resize');
});
