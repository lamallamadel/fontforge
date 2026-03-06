import { test, expect } from '@playwright/test';

const PROJECT_ID = 'proj-1';

test.describe('AI Prompt Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`/studio/${PROJECT_ID}/prompt`);
  });

  test('shows the AI Prompt heading', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'AI Prompt' })).toBeVisible();
  });

  test('renders the prompt input textarea', async ({ page }) => {
    await expect(page.getByTestId('prompt-input')).toBeVisible();
  });

  test('renders suggestion buttons', async ({ page }) => {
    await expect(page.getByText(/bold geometric/i)).toBeVisible();
  });

  test('can type a prompt', async ({ page }) => {
    await page.getByTestId('prompt-input').fill('Create a wide letter M');
    await expect(page.getByTestId('prompt-input')).toHaveValue('Create a wide letter M');
  });

  test('can submit a prompt and see result', async ({ page }) => {
    await page.getByTestId('prompt-input').fill('Generate bold letter A');
    await page.getByRole('button', { name: /generate/i }).click();
    await expect(page.getByTestId('prompt-result')).toBeVisible({ timeout: 15000 });
  });

  test('can click a suggestion to fill input', async ({ page }) => {
    await page.getByText(/bold geometric/i).click();
    const value = await page.getByTestId('prompt-input').inputValue();
    expect(value).toContain('bold geometric');
  });

  test('shows prompt history after submission', async ({ page }) => {
    await page.getByTestId('prompt-input').fill('Test prompt');
    await page.getByRole('button', { name: /generate/i }).click();
    await expect(page.getByTestId('prompt-history')).toBeVisible({ timeout: 15000 });
  });
});
