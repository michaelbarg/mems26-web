import { test, expect } from '@playwright/test';

test('TF clicks fire correct endpoints + chart updates', async ({ page }) => {
  const requests: string[] = [];
  page.on('request', r => requests.push(r.url()));

  await page.goto('http://localhost:3000');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(5000);

  // Click 15m
  const btn15 = page.locator('[data-testid="tf-btn-15m"]');
  await expect(btn15).toBeVisible({ timeout: 10000 });
  await btn15.click();
  await page.waitForTimeout(1000);
  expect(requests.some(u => u.includes('bars15m'))).toBe(true);

  // Click 5m back
  await page.locator('[data-testid="tf-btn-5m"]').click();
  await page.waitForTimeout(1000);

  // Chart should not be shredded
  const chartSvg = page.locator('[data-testid="chart-svg"]');
  await expect(chartSvg).toBeVisible();
});
