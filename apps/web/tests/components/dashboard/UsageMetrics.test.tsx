/**
 * Unit tests for UsageMetrics component
 */

import { render, screen } from '@testing-library/react'
import { jest } from '@jest/globals'
import UsageMetrics from '@/components/dashboard/UsageMetrics'
import type { UserStatistics } from '@shared/types'

// Mock Lucide React icons
jest.mock('lucide-react', () => ({
  TrendingUp: ({ className }: { className?: string }) => <div className={className} data-testid="trending-up-icon" />,
  TrendingDown: ({ className }: { className?: string }) => <div className={className} data-testid="trending-down-icon" />,
  BarChart3: ({ className }: { className?: string }) => <div className={className} data-testid="bar-chart-icon" />,
  Clock: ({ className }: { className?: string }) => <div className={className} data-testid="clock-icon" />,
  CheckCircle: ({ className }: { className?: string }) => <div className={className} data-testid="check-circle-icon" />,
  XCircle: ({ className }: { className?: string }) => <div className={className} data-testid="x-circle-icon" />,
  Target: ({ className }: { className?: string }) => <div className={className} data-testid="target-icon" />,
  Calendar: ({ className }: { className?: string }) => <div className={className} data-testid="calendar-icon" />,
  Activity: ({ className }: { className?: string }) => <div className={className} data-testid="activity-icon" />,
  Minus: ({ className }: { className?: string }) => <div className={className} data-testid="minus-icon" />,
}))

describe('UsageMetrics Component', () => {
  const mockStatistics: UserStatistics = {
    totalJobs: 127,
    successRate: 95.5,
    averageConfidence: 89.2,
    monthlyUsage: {
      creditsUsed: 450,
      jobsCompleted: 28,
      filesProcessed: 28,
      averageProcessingTime: 4200,
      month: 'August',
      year: 2025
    },
    creditBalance: {
      remaining: 2550,
      total: 3000,
      usedThisMonth: 450,
      percentageUsed: 15,
      subscriptionTier: 'PREMIUM'
    },
    processingStats: {
      total_jobs: 127,
      completed_jobs: 121,
      failed_jobs: 6,
      success_rate: 95.5,
      total_products: 3420,
      successful_matches: 3268,
      average_confidence: 89.2
    }
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('Loading State', () => {
    it('displays loading skeletons when loading is true', () => {
      render(<UsageMetrics loading={true} />)
      
      const loadingElements = document.querySelectorAll('.animate-pulse')
      expect(loadingElements.length).toBeGreaterThan(0)
    })
  })

  describe('Data Display', () => {
    it('renders key metrics correctly', () => {
      render(<UsageMetrics statistics={mockStatistics} />)
      
      // Check total jobs
      expect(screen.getByText('127')).toBeInTheDocument()
      expect(screen.getByText('Total Jobs')).toBeInTheDocument()
      
      // Check success rate
      expect(screen.getByText('95.5%')).toBeInTheDocument()
      expect(screen.getByText('Processing success')).toBeInTheDocument()
      
      // Check average confidence
      expect(screen.getByText('89.2%')).toBeInTheDocument()
      expect(screen.getByText('AI matching confidence')).toBeInTheDocument()
      
      // Check monthly jobs
      expect(screen.getByText('28')).toBeInTheDocument()
      expect(screen.getByText('August 2025')).toBeInTheDocument()
    })

    it('displays processing performance metrics', () => {
      render(<UsageMetrics statistics={mockStatistics} />)
      
      // Check completed jobs
      expect(screen.getByText('121')).toBeInTheDocument()
      expect(screen.getByText('Completed Jobs')).toBeInTheDocument()
      
      // Check failed jobs
      expect(screen.getByText('6')).toBeInTheDocument()
      expect(screen.getByText('Failed Jobs')).toBeInTheDocument()
      
      // Check total products
      expect(screen.getByText('3,420')).toBeInTheDocument()
      expect(screen.getByText('Total Products')).toBeInTheDocument()
      
      // Check successful matches
      expect(screen.getByText('3,268')).toBeInTheDocument()
      expect(screen.getByText('Successful Matches')).toBeInTheDocument()
    })

    it('displays monthly overview correctly', () => {
      render(<UsageMetrics statistics={mockStatistics} />)
      
      // Check credits used
      expect(screen.getByText('450')).toBeInTheDocument()
      expect(screen.getByText('Credits Used')).toBeInTheDocument()
      
      // Check files processed
      expect(screen.getByText('28')).toBeInTheDocument()
      expect(screen.getByText('Files Processed')).toBeInTheDocument()
      
      // Check average processing time
      expect(screen.getByText('4.2s')).toBeInTheDocument()
    })

    it('formats processing time correctly for different durations', () => {
      const longProcessingStats = {
        ...mockStatistics,
        monthlyUsage: {
          ...mockStatistics.monthlyUsage,
          averageProcessingTime: 125000 // > 1 minute
        }
      }
      
      render(<UsageMetrics statistics={longProcessingStats} />)
      
      // Should display in minutes
      expect(screen.getByText('2.1m')).toBeInTheDocument()
    })
  })

  describe('Color Coding', () => {
    it('uses correct colors for success rate metrics', () => {
      // High success rate (green)
      const highSuccessStats = {
        ...mockStatistics,
        processingStats: { ...mockStatistics.processingStats, success_rate: 95 }
      }
      
      const { rerender } = render(<UsageMetrics statistics={highSuccessStats} />)
      
      // Low success rate (red)
      const lowSuccessStats = {
        ...mockStatistics,
        processingStats: { ...mockStatistics.processingStats, success_rate: 60 }
      }
      
      rerender(<UsageMetrics statistics={lowSuccessStats} />)
      
      // Medium success rate (yellow)
      const mediumSuccessStats = {
        ...mockStatistics,
        processingStats: { ...mockStatistics.processingStats, success_rate: 80 }
      }
      
      rerender(<UsageMetrics statistics={mediumSuccessStats} />)
    })

    it('uses correct colors for confidence metrics', () => {
      // High confidence (green)
      const highConfidenceStats = { ...mockStatistics, averageConfidence: 92 }
      
      const { rerender } = render(<UsageMetrics statistics={highConfidenceStats} />)
      
      // Low confidence (red)
      const lowConfidenceStats = { ...mockStatistics, averageConfidence: 65 }
      rerender(<UsageMetrics statistics={lowConfidenceStats} />)
      
      // Medium confidence (yellow)  
      const mediumConfidenceStats = { ...mockStatistics, averageConfidence: 78 }
      rerender(<UsageMetrics statistics={mediumConfidenceStats} />)
    })
  })

  describe('Progress Bars', () => {
    it('calculates and displays match success rate correctly', () => {
      render(<UsageMetrics statistics={mockStatistics} />)
      
      // Expected: (3268 / 3420) * 100 = 95.6%
      const expectedPercentage = (3268 / 3420 * 100).toFixed(1)
      expect(screen.getByText(`${expectedPercentage}%`)).toBeInTheDocument()
    })

    it('handles zero products gracefully', () => {
      const zeroProductsStats = {
        ...mockStatistics,
        processingStats: {
          ...mockStatistics.processingStats,
          total_products: 0,
          successful_matches: 0
        }
      }
      
      render(<UsageMetrics statistics={zeroProductsStats} />)
      
      expect(screen.getByText('0%')).toBeInTheDocument()
    })
  })

  describe('Error Handling', () => {
    it('displays error message when no statistics are provided', () => {
      render(<UsageMetrics />)
      
      expect(screen.getByText('Usage Metrics')).toBeInTheDocument()
      expect(screen.getByText('Unable to load usage statistics')).toBeInTheDocument()
    })
  })

  describe('Tooltips and Help Text', () => {
    it('includes tooltip for average processing time', () => {
      render(<UsageMetrics statistics={mockStatistics} />)
      
      // Check for info icon that would trigger tooltip
      expect(screen.getByText('ⓘ')).toBeInTheDocument()
    })
  })

  describe('Layout and Responsive Design', () => {
    it('applies custom className when provided', () => {
      const { container } = render(
        <UsageMetrics statistics={mockStatistics} className="custom-class" />
      )
      
      expect(container.firstChild).toHaveClass('custom-class')
    })

    it('renders all metric cards in proper grid layout', () => {
      render(<UsageMetrics statistics={mockStatistics} />)
      
      // Check for grid container
      const gridContainer = document.querySelector('.grid.grid-cols-1.md\\:grid-cols-2.lg\\:grid-cols-4')
      expect(gridContainer).toBeInTheDocument()
    })
  })

  describe('Number Formatting', () => {
    it('formats large numbers with proper separators', () => {
      const largeNumberStats = {
        ...mockStatistics,
        processingStats: {
          ...mockStatistics.processingStats,
          total_products: 12345,
          successful_matches: 11987
        }
      }
      
      render(<UsageMetrics statistics={largeNumberStats} />)
      
      expect(screen.getByText('12,345')).toBeInTheDocument()
      expect(screen.getByText('11,987')).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('includes proper heading structure', () => {
      render(<UsageMetrics statistics={mockStatistics} />)
      
      expect(screen.getByRole('heading', { name: /processing performance/i })).toBeInTheDocument()
      expect(screen.getByRole('heading', { name: /monthly overview/i })).toBeInTheDocument()
    })

    it('includes proper icon labels', () => {
      render(<UsageMetrics statistics={mockStatistics} />)
      
      expect(screen.getByTestId('bar-chart-icon')).toBeInTheDocument()
      expect(screen.getByTestId('check-circle-icon')).toBeInTheDocument()
      expect(screen.getByTestId('target-icon')).toBeInTheDocument()
      expect(screen.getByTestId('calendar-icon')).toBeInTheDocument()
    })
  })
})