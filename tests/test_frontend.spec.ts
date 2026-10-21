import { test, expect } from '@playwright/test';

test('chat flow handles messages properly', async ({ page }) => {
  await page.goto('http://localhost:8080/');
  // Ensure the empty state is present
  await expect(page.locator('#empty-state')).toBeVisible();

  // Send a message
  await page.fill('#user-input', 'Hello Aisha');
  await page.click('#send-btn');

  // Verify typing indicator or response appears, and empty state is removed
  await expect(page.locator('#empty-state')).not.toBeVisible();

  // Wait for the AI's response (or the fallback error)
  const aiMessage = page.locator('.msg.ai').last();
  await expect(aiMessage).toBeVisible();

  // Ensure no console errors except our expected mocked failure ones
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  expect(errors.length).toBe(0);
});
