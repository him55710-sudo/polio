import { test, expect } from '@playwright/test';

test.describe('Trust UX and Grounding Validation', () => {
  test('Renders ClaimGroundingPanel and support badges correctly', async ({ page }) => {
    // Navigate to a mocked diagnosis result page
    await page.goto('/app/diagnosis/mock-id'); // Assuming mock route or interception

    // Wait for the grounding panel to appear
    const panel = page.getByTestId('claim-grounding-panel');
    await expect(panel).toBeVisible();

    // Verify badges
    const supportedBadge = page.locator('span:has-text("Supported")').first();
    const unsupportedBadge = page.locator('span:has-text("Unsupported")').first();
    
    // Check if badges are rendered
    await expect(supportedBadge).toBeVisible();
    
    // If unsupported claims exist, warning ribbon should be visible
    const warningRibbon = page.locator('text=주의: 증명되지 않은 주장이 포함되어 있습니다.');
    await expect(warningRibbon).toBeVisible();
  });

  test('Evidence can be expanded and collapsed', async ({ page }) => {
    await page.goto('/app/diagnosis/mock-id');
    
    const expandButton = page.locator('button:has-text("View")').first();
    await expect(expandButton).toBeVisible();
    
    // Click to expand evidence
    await expandButton.click();
    
    // Expect the source excerpt to become visible
    const excerpt = page.locator('p.italic').first();
    await expect(excerpt).toBeVisible();

    // Click again to hide
    await page.locator('button:has-text("Hide Source Evidence")').first().click();
    await expect(excerpt).not.toBeVisible();
  });

  test('Async job progress UI renders granular stages', async ({ page }) => {
    // Simulate a running job
    await page.goto('/app/diagnosis/running-mock-id');
    
    const statusCard = page.getByTestId('diagnosis-job-status');
    await expect(statusCard).toBeVisible();
    
    // Check for progress stage labels and history
    await expect(page.locator('text=Current Stage')).toBeVisible();
    // Example: "Parsing PDF..." should be visible
    await expect(page.locator('text=Processing')).toBeVisible();
  });

  test('CodeRunner Pyodide lazily loads without blocking critical paths', async ({ page }) => {
    await page.goto('/app/workshop/mock-id');
    
    // The "Initialize Engine" button should be visible instead of loading immediately
    const initBtn = page.locator('button:has-text("Initialize Engine")');
    await expect(initBtn).toBeVisible();

    // Clicking it triggers Pyodide load
    await initBtn.click();
    await expect(page.locator('button:has-text("Initializing...")')).toBeVisible();
    
    // After load, "Run Sandbox" appears
    await expect(page.locator('button:has-text("Run Sandbox")')).toBeVisible({ timeout: 15000 });
  });

  test('Unsupported filter functionality', async ({ page }) => {
    await page.goto('/app/diagnosis/mock-id');
    const filterBtn = page.locator('button:has-text("검증 필요 주장만 보기")');
    await expect(filterBtn).toBeVisible();
    
    await filterBtn.click();
    // After clicking, the active state text should appear
    await expect(page.locator('button:has-text("(Active)")')).toBeVisible();
  });
});
