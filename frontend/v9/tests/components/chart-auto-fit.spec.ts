import { test, expect } from '@playwright/test';

test('C12: Auto-fit button shows when zoomed, hides on click', async ({ page }) => {
  await page.goto('http://localhost:3000');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(5000);

  const chart = page.locator('[data-testid="chart-svg"]');
  await expect(chart).toBeVisible({ timeout: 10000 });

  // Auto-fit should be hidden initially (no manual zoom)
  const autoBtn = page.locator('[data-testid="chart-auto-fit-btn"]');

  // Trigger zoom via wheel
  await chart.hover();
  await page.mouse.wheel(0, -120);
  await page.waitForTimeout(500);

  // Auto-fit button should now be visible
  await expect(autoBtn).toBeVisible({ timeout: 5000 });

  // Click auto-fit → resets zoom → button hides
  await autoBtn.click();
  await page.waitForTimeout(500);
  await expect(autoBtn).not.toBeVisible({ timeout: 5000 });
});
