import { test, expect } from '@playwright/test';

test('C09: Y-axis drag region exists and is interactive', async ({ page }) => {
  await page.goto('http://localhost:3000');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(5000);

  const yAxis = page.locator('[data-testid="chart-yaxis-region"]');
  await expect(yAxis).toBeVisible({ timeout: 10000 });

  // Verify cursor is ns-resize
  const cursor = await yAxis.getAttribute('cursor');
  expect(cursor).toBe('ns-resize');
});
