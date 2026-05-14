import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests',
  use: {
    baseURL: 'http://localhost:3000',
    headless: true,
    viewport: { width: 1440, height: 900 },
    actionTimeout: 10000,
  },
  reporter: [['json', { outputFile: '/tmp/master-ui-run/playwright-report.json' }], ['list']],
  retries: 0,
});
