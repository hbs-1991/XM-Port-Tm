import { test, expect, Page } from '@playwright/test';
import { join } from 'path';

// Test data files
const VALID_CSV_CONTENT = `Product Description,Quantity,Unit,Value,Origin Country,Unit Price
"Test Product 1",100,pieces,500.00,USA,5.00
"Test Product 2",50,kg,250.50,Canada,5.01
"Test Product 3",75,units,375.00,Mexico,5.00
"Test Product 4",200,pieces,1000.00,Germany,5.00
"Test Product 5",30,kg,150.00,France,5.00`;

const INVALID_CSV_CONTENT = `Product,Qty,Price
"Test Product 1",100,500.00
"Test Product 2",50,250.50`;

const LARGE_CSV_CONTENT = `Product Description,Quantity,Unit,Value,Origin Country,Unit Price
${Array.from({ length: 1000 }, (_, i) => 
  `"Product ${i + 1}",${i + 1},pieces,${(i + 1) * 5.0},USA,5.00`
).join('\n')}`;

// Helper function to create temporary files
async function createTestFile(page: Page, filename: string, content: string): Promise<void> {
  await page.evaluate(({ filename, content }) => {
    const blob = new Blob([content], { type: 'text/csv' });
    const file = new File([blob], filename, { type: 'text/csv' });
    // Store file in window for test access
    (window as any).testFile = file;
  }, { filename, content });
}

// Mock API responses
async function mockAPIResponses(page: Page) {
  // Mock validation endpoint
  await page.route('**/api/v1/processing/validate', async route => {
    const request = route.request();
    const formData = await request.formData();
    const file = formData.get('file') as File;
    
    if (file?.name.includes('invalid')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          isValid: false,
          totalRows: 2,
          validRows: 0,
          errors: [
            { field: 'headers', row: 1, error: 'Missing required column: Product Description' },
            { field: 'headers', row: 1, error: 'Missing required column: Unit Price' },
          ],
          warnings: [],
        }),
      });
    } else {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          isValid: true,
          totalRows: 5,
          validRows: 5,
          errors: [],
          warnings: [],
          summary: {
            dataQualityScore: 100,
            totalErrors: 0,
            errorsByField: {},
            errorsByType: {},
            mostCommonErrors: [],
          },
        }),
      });
    }
  });

  // Mock upload endpoint
  await page.route('**/api/v1/processing/upload', async route => {
    await page.waitForTimeout(1000); // Simulate upload time
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        jobId: 'test-job-123',
        message: 'File uploaded successfully',
        status: 'PENDING',
      }),
    });
  });

  // Mock credit check endpoint
  await page.route('**/api/v1/auth/credits', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        creditsRemaining: 100,
        creditsUsedThisMonth: 20,
      }),
    });
  });
}

test.describe('File Upload Workflow - E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    await mockAPIResponses(page);
  });

  test.describe('Complete Upload Workflow', () => {
    test('should complete successful file upload workflow', async ({ page }) => {
      await page.goto('/dashboard/upload');

      // Wait for page to load
      await expect(page.locator('[data-testid="file-upload-container"]')).toBeVisible();

      // Create and select valid CSV file
      await createTestFile(page, 'valid_test.csv', VALID_CSV_CONTENT);

      // Use file input to select file
      const fileInput = page.locator('[data-testid="file-input"]');
      await fileInput.setInputFiles({
        name: 'valid_test.csv',
        mimeType: 'text/csv',
        buffer: Buffer.from(VALID_CSV_CONTENT)
      });

      // Wait for validation to complete
      await expect(page.locator('text=Validating file')).toBeVisible();
      await expect(page.locator('text=Validation successful')).toBeVisible();

      // Verify validation results displayed
      await expect(page.locator('text=Data Quality: 100%')).toBeVisible();
      await expect(page.locator('text=5 of 5 rows valid')).toBeVisible();

      // Verify upload button is enabled
      const uploadButton = page.locator('button:has-text("Upload File")');
      await expect(uploadButton).toBeEnabled();

      // Click upload button
      await uploadButton.click();

      // Verify upload progress
      await expect(page.locator('text=Uploading file')).toBeVisible();
      await expect(page.locator('[role="progressbar"]')).toBeVisible();

      // Verify cancel button during upload
      await expect(page.locator('button:has-text("Cancel")')).toBeVisible();

      // Wait for upload completion
      await expect(page.locator('text=Upload successful')).toBeVisible();
      await expect(page.locator('text=Job ID: test-job-123')).toBeVisible();

      // Verify success state
      await expect(page.locator('text=File uploaded successfully')).toBeVisible();
    });

    test('should handle validation errors correctly', async ({ page }) => {
      await page.goto('/dashboard/upload');

      await expect(page.locator('[data-testid="file-upload-container"]')).toBeVisible();

      // Select invalid CSV file
      const fileInput = page.locator('[data-testid="file-input"]');
      await fileInput.setInputFiles({
        name: 'invalid_test.csv',
        mimeType: 'text/csv',
        buffer: Buffer.from(INVALID_CSV_CONTENT)
      });

      // Wait for validation to complete
      await expect(page.locator('text=Validating file')).toBeVisible();
      await expect(page.locator('text=Validation failed')).toBeVisible();

      // Verify error messages displayed
      await expect(page.locator('text=Missing required column: Product Description')).toBeVisible();
      await expect(page.locator('text=Missing required column: Unit Price')).toBeVisible();

      // Verify upload button is disabled
      const uploadButton = page.locator('button:has-text("Upload File")');
      await expect(uploadButton).toBeDisabled();

      // Verify retry option
      await expect(page.locator('button:has-text("Retry Validation")')).toBeVisible();
      await expect(page.locator('button:has-text("Choose Different File")')).toBeVisible();
    });

    test('should handle large file upload with progress tracking', async ({ page }) => {
      await page.goto('/dashboard/upload');

      await expect(page.locator('[data-testid="file-upload-container"]')).toBeVisible();

      // Select large CSV file
      const fileInput = page.locator('[data-testid="file-input"]');
      await fileInput.setInputFiles({
        name: 'large_test.csv',
        mimeType: 'text/csv',
        buffer: Buffer.from(LARGE_CSV_CONTENT)
      });

      // Wait for validation
      await expect(page.locator('text=Validating file')).toBeVisible();

      // For large files, validation might take longer
      await expect(page.locator('text=Validation successful')).toBeVisible({ timeout: 10000 });

      // Verify large file stats
      await expect(page.locator('text=1000 rows processed')).toBeVisible();

      // Start upload
      const uploadButton = page.locator('button:has-text("Upload File")');
      await uploadButton.click();

      // Verify upload progress indicators
      await expect(page.locator('text=Uploading file')).toBeVisible();
      await expect(page.locator('[role="progressbar"]')).toBeVisible();

      // Verify file size information
      await expect(page.locator('text=large_test.csv')).toBeVisible();
    });
  });

  test.describe('Drag and Drop Functionality', () => {
    test('should support drag and drop file upload', async ({ page }) => {
      await page.goto('/dashboard/upload');

      await expect(page.locator('[data-testid="file-upload-container"]')).toBeVisible();

      // Create file content
      const dataTransfer = await page.evaluateHandle((csvContent) => {
        const dt = new DataTransfer();
        const file = new File([csvContent], 'dragged_file.csv', { type: 'text/csv' });
        dt.items.add(file);
        return dt;
      }, VALID_CSV_CONTENT);

      // Simulate drag and drop
      const dropzone = page.locator('[data-testid="dropzone"]');
      
      // Trigger dragenter event
      await dropzone.dispatchEvent('dragenter', { dataTransfer });
      
      // Verify drag state styling
      await expect(dropzone).toHaveClass(/drag-active/);
      
      // Trigger drop event
      await dropzone.dispatchEvent('drop', { dataTransfer });

      // Verify file processing starts
      await expect(page.locator('text=Validating file')).toBeVisible();
      await expect(page.locator('text=Validation successful')).toBeVisible();
    });

    test('should show appropriate feedback for rejected files during drag', async ({ page }) => {
      await page.goto('/dashboard/upload');

      await expect(page.locator('[data-testid="file-upload-container"]')).toBeVisible();

      // Create invalid file type
      const dataTransfer = await page.evaluateHandle(() => {
        const dt = new DataTransfer();
        const file = new File(['invalid content'], 'document.pdf', { type: 'application/pdf' });
        dt.items.add(file);
        return dt;
      });

      const dropzone = page.locator('[data-testid="dropzone"]');
      
      // Simulate drag of invalid file
      await dropzone.dispatchEvent('dragenter', { dataTransfer });
      
      // Should show rejection state
      await expect(dropzone).toHaveClass(/drag-reject/);
      
      // Drop the file
      await dropzone.dispatchEvent('drop', { dataTransfer });
      
      // Verify error message
      await expect(page.locator('text=Only CSV and XLSX files are allowed')).toBeVisible();
    });
  });

  test.describe('Error Handling and Recovery', () => {
    test('should handle network errors during upload', async ({ page }) => {
      // Override mock to simulate network error
      await page.route('**/api/v1/processing/upload', route => {
        route.abort('failed');
      });

      await page.goto('/dashboard/upload');
      await expect(page.locator('[data-testid="file-upload-container"]')).toBeVisible();

      // Select file and validate
      const fileInput = page.locator('[data-testid="file-input"]');
      await fileInput.setInputFiles({
        name: 'test.csv',
        mimeType: 'text/csv',
        buffer: Buffer.from(VALID_CSV_CONTENT)
      });

      await expect(page.locator('text=Validation successful')).toBeVisible();

      // Attempt upload
      const uploadButton = page.locator('button:has-text("Upload File")');
      await uploadButton.click();

      // Verify error handling
      await expect(page.locator('text=Upload failed')).toBeVisible();
      await expect(page.locator('text=Network error')).toBeVisible();
      
      // Verify retry option
      await expect(page.locator('button:has-text("Try Again")')).toBeVisible();
    });

    test('should handle server errors gracefully', async ({ page }) => {
      // Mock server error
      await page.route('**/api/v1/processing/upload', route => {
        route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({
            error: 'Internal server error',
            message: 'Database connection failed'
          }),
        });
      });

      await page.goto('/dashboard/upload');
      await expect(page.locator('[data-testid="file-upload-container"]')).toBeVisible();

      const fileInput = page.locator('[data-testid="file-input"]');
      await fileInput.setInputFiles({
        name: 'test.csv',
        mimeType: 'text/csv',
        buffer: Buffer.from(VALID_CSV_CONTENT)
      });

      await expect(page.locator('text=Validation successful')).toBeVisible();

      const uploadButton = page.locator('button:has-text("Upload File")');
      await uploadButton.click();

      // Verify server error handling
      await expect(page.locator('text=Upload failed: Database connection failed')).toBeVisible();
      await expect(page.locator('button:has-text("Try Again")')).toBeVisible();
    });

    test('should handle insufficient credits error', async ({ page }) => {
      // Mock insufficient credits response
      await page.route('**/api/v1/processing/upload', route => {
        route.fulfill({
          status: 402,
          contentType: 'application/json',
          body: JSON.stringify({
            error: 'Insufficient credits',
            message: 'You need 5 credits but only have 2 remaining',
            creditsRequired: 5,
            creditsRemaining: 2
          }),
        });
      });

      await page.goto('/dashboard/upload');
      await expect(page.locator('[data-testid="file-upload-container"]')).toBeVisible();

      const fileInput = page.locator('[data-testid="file-input"]');
      await fileInput.setInputFiles({
        name: 'test.csv',
        mimeType: 'text/csv',
        buffer: Buffer.from(VALID_CSV_CONTENT)
      });

      await expect(page.locator('text=Validation successful')).toBeVisible();

      const uploadButton = page.locator('button:has-text("Upload File")');
      await uploadButton.click();

      // Verify credit error handling
      await expect(page.locator('text=Insufficient credits')).toBeVisible();
      await expect(page.locator('text=You need 5 credits but only have 2 remaining')).toBeVisible();
      await expect(page.locator('button:has-text("Purchase Credits")')).toBeVisible();
    });

    test('should support upload cancellation', async ({ page }) => {
      // Mock slow upload
      let resolveUpload: () => void;
      await page.route('**/api/v1/processing/upload', route => {
        return new Promise(resolve => {
          resolveUpload = () => {
            route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify({
                jobId: 'test-job-123',
                message: 'Upload successful'
              }),
            });
            resolve(undefined);
          };
        });
      });

      await page.goto('/dashboard/upload');
      await expect(page.locator('[data-testid="file-upload-container"]')).toBeVisible();

      const fileInput = page.locator('[data-testid="file-input"]');
      await fileInput.setInputFiles({
        name: 'test.csv',
        mimeType: 'text/csv',
        buffer: Buffer.from(VALID_CSV_CONTENT)
      });

      await expect(page.locator('text=Validation successful')).toBeVisible();

      const uploadButton = page.locator('button:has-text("Upload File")');
      await uploadButton.click();

      // Verify upload progress
      await expect(page.locator('text=Uploading file')).toBeVisible();

      // Cancel upload
      const cancelButton = page.locator('button:has-text("Cancel")');
      await cancelButton.click();

      // Verify cancellation
      await expect(page.locator('text=Upload cancelled')).toBeVisible();
      await expect(page.locator('text=Drag & drop your file here')).toBeVisible();
    });
  });

  test.describe('Data Preview and Validation', () => {
    test('should display data preview with pagination', async ({ page }) => {
      await page.goto('/dashboard/upload');
      await expect(page.locator('[data-testid="file-upload-container"]')).toBeVisible();

      const fileInput = page.locator('[data-testid="file-input"]');
      await fileInput.setInputFiles({
        name: 'test.csv',
        mimeType: 'text/csv',
        buffer: Buffer.from(LARGE_CSV_CONTENT)
      });

      await expect(page.locator('text=Validation successful')).toBeVisible();

      // Verify data preview section
      await expect(page.locator('text=Data Preview')).toBeVisible();

      // Check if data is displayed
      await expect(page.locator('text=Product 1')).toBeVisible();
      await expect(page.locator('text=pieces')).toBeVisible();
      await expect(page.locator('text=5.00')).toBeVisible();

      // Verify pagination for large dataset
      await expect(page.locator('text=Showing 1-10 of 1000 rows')).toBeVisible();

      // Test pagination
      const nextButton = page.locator('button:has-text("Next")');
      if (await nextButton.isEnabled()) {
        await nextButton.click();
        await expect(page.locator('text=Product 11')).toBeVisible();
      }
    });

    test('should show detailed validation summary', async ({ page }) => {
      await page.goto('/dashboard/upload');
      await expect(page.locator('[data-testid="file-upload-container"]')).toBeVisible();

      const fileInput = page.locator('[data-testid="file-input"]');
      await fileInput.setInputFiles({
        name: 'test.csv',
        mimeType: 'text/csv',
        buffer: Buffer.from(VALID_CSV_CONTENT)
      });

      await expect(page.locator('text=Validation successful')).toBeVisible();

      // Verify validation summary
      await expect(page.locator('text=Data Quality: 100%')).toBeVisible();
      await expect(page.locator('text=5 of 5 rows valid')).toBeVisible();
      await expect(page.locator('text=No errors found')).toBeVisible();

      // Check for processing cost
      await expect(page.locator('text=Processing will cost 1 credit')).toBeVisible();
    });
  });

  test.describe('Performance and Accessibility', () => {
    test('should handle multiple file selections', async ({ page }) => {
      await page.goto('/dashboard/upload');
      await expect(page.locator('[data-testid="file-upload-container"]')).toBeVisible();

      const fileInput = page.locator('[data-testid="file-input"]');

      // Select first file
      await fileInput.setInputFiles({
        name: 'first.csv',
        mimeType: 'text/csv',
        buffer: Buffer.from(VALID_CSV_CONTENT)
      });

      await expect(page.locator('text=Validation successful')).toBeVisible();

      // Replace with second file
      await fileInput.setInputFiles({
        name: 'second.csv',
        mimeType: 'text/csv',
        buffer: Buffer.from(VALID_CSV_CONTENT)
      });

      // Should validate new file
      await expect(page.locator('text=Validating file')).toBeVisible();
      await expect(page.locator('text=Validation successful')).toBeVisible();

      // Should show new filename
      await expect(page.locator('text=second.csv')).toBeVisible();
    });

    test('should be keyboard accessible', async ({ page }) => {
      await page.goto('/dashboard/upload');
      await expect(page.locator('[data-testid="file-upload-container"]')).toBeVisible();

      // Test keyboard navigation
      await page.keyboard.press('Tab');
      
      // Should focus on dropzone
      const dropzone = page.locator('[data-testid="dropzone"]');
      await expect(dropzone).toBeFocused();

      // Should activate file dialog on Enter
      await page.keyboard.press('Enter');
      
      // Verify accessibility attributes
      await expect(dropzone).toHaveAttribute('role', 'button');
      await expect(dropzone).toHaveAttribute('tabindex', '0');
    });

    test('should provide screen reader announcements', async ({ page }) => {
      await page.goto('/dashboard/upload');
      await expect(page.locator('[data-testid="file-upload-container"]')).toBeVisible();

      const fileInput = page.locator('[data-testid="file-input"]');
      await fileInput.setInputFiles({
        name: 'test.csv',
        mimeType: 'text/csv',
        buffer: Buffer.from(VALID_CSV_CONTENT)
      });

      // Check for ARIA live regions
      const statusRegion = page.locator('[role="status"]');
      await expect(statusRegion).toBeVisible();

      // Should announce validation completion
      await expect(page.locator('text=Validation successful')).toBeVisible();
      await expect(statusRegion).toContainText('Validation successful');
    });
  });

  test.describe('Mobile Responsiveness', () => {
    test('should work on mobile devices', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 }); // iPhone SE
      
      await page.goto('/dashboard/upload');
      await expect(page.locator('[data-testid="file-upload-container"]')).toBeVisible();

      // Verify mobile layout
      const dropzone = page.locator('[data-testid="dropzone"]');
      await expect(dropzone).toBeVisible();

      // Test file upload on mobile
      const fileInput = page.locator('[data-testid="file-input"]');
      await fileInput.setInputFiles({
        name: 'mobile_test.csv',
        mimeType: 'text/csv',
        buffer: Buffer.from(VALID_CSV_CONTENT)
      });

      await expect(page.locator('text=Validation successful')).toBeVisible();

      // Verify mobile-friendly buttons
      const uploadButton = page.locator('button:has-text("Upload File")');
      await expect(uploadButton).toBeVisible();
      
      // Should be large enough for touch
      const buttonBox = await uploadButton.boundingBox();
      expect(buttonBox?.height).toBeGreaterThan(40); // Minimum touch target
    });
  });
});