Implementation Tasks

  Task 1: Backend API Enhancement (3 hours)

  File: apps/api/src/api/v1/processing.py

  1. Modify the get_job_products endpoint to include HS code data:

  @router.get("/jobs/{job_id}/products")
  async def get_job_products(
      job_id: UUID,
      current_user: User = Depends(get_current_user),
      db: Session = Depends(get_db)
  ) -> List[ProductDataWithHS]:
      # Fetch job and validate ownership
      job = db.query(ProcessingJob).filter(
          ProcessingJob.id == job_id,
          ProcessingJob.user_id == current_user.id
      ).first()

      # Join with ProductMatch to get HS codes
      products = db.query(ProductMatch).filter(
          ProductMatch.job_id == job_id
      ).all()

      return [
          ProductDataWithHS(
              product_description=p.product_description,
              quantity=p.quantity,
              unit_of_measure=p.unit_of_measure,
              value=p.value,
              origin_country=p.origin_country,
              hs_code=p.matched_hs_code,
              confidence_score=p.confidence_score,
              alternative_hs_codes=p.alternative_hs_codes,
              requires_review=p.requires_manual_review
          )
          for p in products
      ]

  2. Create new schema in apps/api/src/schemas/processing.py:

  class ProductDataWithHS(ProductData):
      hs_code: str
      confidence_score: float
      alternative_hs_codes: Optional[List[str]] = []
      requires_review: bool = False

      class Config:
          schema_extra = {
              "example": {
                  "product_description": "Cotton T-Shirt",
                  "quantity": 100,
                  "unit_of_measure": "PCS",
                  "value": 1500.00,
                  "origin_country": "USA",
                  "hs_code": "6109.10.00",
                  "confidence_score": 0.95,
                  "alternative_hs_codes": ["6109.90.10", "6105.10.00"],
                  "requires_review": False
              }
          }

  Task 2: WebSocket Enhancement (2 hours)

  File: apps/api/src/api/v1/ws.py

  Add HS code completion notification:

  async def notify_hs_matching_complete(job_id: str, user_id: str):
      message = {
          "type": "hs_matching_complete",
          "job_id": job_id,
          "timestamp": datetime.utcnow().isoformat(),
          "message": "HS code matching completed"
      }
      await manager.send_personal_message(json.dumps(message), user_id)

  File: apps/api/src/services/file_processing.py

  Update to trigger WebSocket after matching:

  # After HS matching completes
  await ws_manager.send_job_update(
      user_id=str(user.id),
      job_id=str(job.id),
      status="hs_matching_complete",
      message="HS codes have been matched",
      data={"products_matched": len(products)}
  )

  Task 3: Frontend Component Updates (4 hours)

  File: apps/web/src/components/dashboard/upload/EditableSpreadsheet.tsx

  1. Update interface and state:

  interface ProductWithHS {
    'Product Description': string;
    'Quantity': number;
    'Unit': string;
    'Value': number;
    'Origin Country': string;
    'Unit Price': number;
    'HS Code'?: string;
    'Confidence'?: number;
    'Alternative Codes'?: string[];
  }

  interface EditableSpreadsheetProps {
    data: ProductWithHS[];
    fileName: string;
    jobId?: string;
    onDataChange?: (data: ProductWithHS[]) => void;
    onSave?: (data: ProductWithHS[]) => Promise<void>;
    maxRows?: number;
    readOnly?: boolean;
    showHSCodes?: boolean; // New prop
  }

  2. Add HS Code column with confidence badges:

  import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from
  '@/components/shared/ui/tooltip';

  // Add to columns array
  const columns = localData.length > 0 ? Object.keys(localData[0]) : [
    'Product Description',
    'Quantity',
    'Unit',
    'Value',
    'Origin Country',
    'Unit Price',
    ...(showHSCodes ? ['HS Code'] : [])
  ];

  // Confidence level helper
  const getConfidenceBadge = (confidence: number) => {
    if (confidence >= 0.95) {
      return <Badge className="bg-green-500">High</Badge>;
    } else if (confidence >= 0.8) {
      return <Badge className="bg-yellow-500">Medium</Badge>;
    } else {
      return <Badge className="bg-red-500">Low</Badge>;
    }
  };

  // In the table cell rendering
  {column === 'HS Code' && row.HS_Code ? (
    <div className="flex items-center gap-2">
      <span className="font-mono">{row['HS Code']}</span>
      {row.Confidence && getConfidenceBadge(row.Confidence)}
      {row['Alternative Codes']?.length > 0 && (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger>
              <InfoCircle className="h-4 w-4 text-gray-400" />
            </TooltipTrigger>
            <TooltipContent>
              <div className="text-sm">
                <p className="font-semibold mb-1">Alternative codes:</p>
                {row['Alternative Codes'].map((code, idx) => (
                  <p key={idx} className="font-mono">{code}</p>
                ))}
              </div>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}
    </div>
  ) : (
    <span>{row[column]}</span>
  )}

  3. Add HS Code validation:

  const validateHSCode = (code: string): boolean => {
    // HS codes are typically 6-10 digits with optional dots
    const hsCodePattern = /^\d{4}(\.\d{2}){0,2}$/;
    return hsCodePattern.test(code);
  };

  // In validation function
  if (column === 'HS Code' && value) {
    if (!validateHSCode(value)) {
      errors.push({
        row: index,
        column,
        message: 'Invalid HS code format (e.g., 6109.10.00)'
      });
    }
  }

  Task 4: WebSocket Integration (2 hours)

  File: apps/web/src/hooks/useProcessingUpdates.ts

  Create or update hook for real-time updates:

  import { useEffect, useState } from 'react';
  import { useWebSocket } from '@/hooks/useWebSocket';

  export function useProcessingUpdates(jobId: string) {
    const [hsCodesReady, setHsCodesReady] = useState(false);
    const [products, setProducts] = useState<ProductWithHS[]>([]);
    const { lastMessage } = useWebSocket();

    useEffect(() => {
      if (lastMessage) {
        const data = JSON.parse(lastMessage);

        if (data.type === 'hs_matching_complete' && data.job_id === jobId) {
          setHsCodesReady(true);
          // Fetch updated products with HS codes
          fetchProductsWithHS(jobId);
        }
      }
    }, [lastMessage, jobId]);

    const fetchProductsWithHS = async (jobId: string) => {
      try {
        const response = await fetch(`/api/v1/processing/jobs/${jobId}/products`);
        const data = await response.json();
        setProducts(data);
      } catch (error) {
        console.error('Failed to fetch products with HS codes:', error);
      }
    };

    return { hsCodesReady, products };
  }

  File: apps/web/src/app/dashboard/upload/page.tsx

  Integrate the hook:

  export default function UploadPage() {
    const { jobId, fileData } = useFileUpload();
    const { hsCodesReady, products } = useProcessingUpdates(jobId);

    // Merge HS codes into spreadsheet data when ready
    useEffect(() => {
      if (hsCodesReady && products.length > 0) {
        const updatedData = fileData.map((row, index) => ({
          ...row,
          'HS Code': products[index]?.hs_code || '',
          'Confidence': products[index]?.confidence_score || 0,
          'Alternative Codes': products[index]?.alternative_hs_codes || []
        }));
        setFileData(updatedData);
      }
    }, [hsCodesReady, products]);

    return (
      <EditableSpreadsheet
        data={fileData}
        fileName={fileName}
        jobId={jobId}
        showHSCodes={hsCodesReady}
        onDataChange={handleDataChange}
      />
    );
  }

  Task 5: Manual HS Code Editing (2 hours)

  File: apps/web/src/services/processing.ts

  Add endpoint for updating HS codes:

  export async function updateProductHSCode(
    jobId: string,
    productIndex: number,
    hsCode: string
  ): Promise<void> {
    const response = await fetch(
      `/api/v1/processing/jobs/${jobId}/products/${productIndex}/hs-code`,
      {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ hs_code: hsCode }),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to update HS code');
    }
  }

  🧪 Testing Requirements

  Unit Tests

  File: apps/api/tests/unit/test_hs_code_display.py

  async def test_get_products_with_hs_codes():
      """Test that products endpoint returns HS code data"""
      # Create test job with product matches
      # Call endpoint
      # Assert HS codes are included in response
      pass

  async def test_websocket_hs_notification():
      """Test WebSocket sends HS matching complete notification"""
      # Create WebSocket connection
      # Trigger HS matching completion
      # Assert notification received
      pass

  File: apps/web/tests/components/dashboard/upload/EditableSpreadsheet.test.tsx

  describe('EditableSpreadsheet HS Code Display', () => {
    it('displays HS code column when showHSCodes is true', () => {
      // Test implementation
    });

    it('shows confidence badges with correct colors', () => {
      // Test implementation
    });

    it('validates HS code format on edit', () => {
      // Test implementation
    });
  });

  Integration Tests

  // apps/web/tests/e2e/hs-code-display.spec.ts
  test('HS codes appear after processing', async ({ page }) => {
    // Upload file
    // Wait for processing
    // Assert HS codes visible in spreadsheet
    // Test editing functionality
  });

  📝 Documentation Updates

  1. Update API documentation with new endpoints
  2. Add HS code display to user guide
  3. Document WebSocket message types

  ✅ Definition of Done Checklist

  - Backend API returns HS code data
  - WebSocket sends HS matching notifications
  - EditableSpreadsheet displays HS code column
  - Confidence badges show correct colors
  - Alternative codes show in tooltip
  - Manual editing works with validation
  - Real-time updates via WebSocket functional
  - All tests passing (unit + integration)
  - Code review completed
  - Documentation updated
  - No console errors or warnings
  - Performance acceptable (< 100ms render)
  - Responsive on mobile devices
  - Accessibility requirements met (ARIA labels)

  ⚠️ Technical Considerations

  1. Performance: For large datasets (>1000 rows), implement virtual scrolling
  2. Caching: Cache HS codes in localStorage for offline viewing
  3. Error Handling: Graceful degradation if HS matching service unavailable
  4. Security: Validate HS code edits server-side to prevent injection
  5. Backwards Compatibility: Ensure old jobs without HS codes still display

  🚀 Deployment Notes

  1. Run database migrations if schema changes needed
  2. Update environment variables if new configs added
  3. Clear Redis cache after deployment
  4. Monitor WebSocket connections for stability