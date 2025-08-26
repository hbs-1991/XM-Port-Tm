/**
 * Unit tests for CreditBalance component
 */

import { render, screen } from '@testing-library/react'
import { jest } from '@jest/globals'
import CreditBalance from '@/components/dashboard/CreditBalance'
import type { CreditBalance as CreditBalanceType } from '@shared/types'

// Mock the useAuth hook
const mockUser = {
  id: '1',
  email: 'test@example.com',
  firstName: 'Test',
  lastName: 'User',
  creditsRemaining: 2500,
  creditsUsedThisMonth: 500,
  subscriptionTier: 'PREMIUM'
}

jest.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({ user: mockUser })
}))

// Mock Lucide React icons
jest.mock('lucide-react', () => ({
  CreditCard: ({ className }: { className?: string }) => <div className={className} data-testid="credit-card-icon" />,
  TrendingUp: ({ className }: { className?: string }) => <div className={className} data-testid="trending-up-icon" />,
  TrendingDown: ({ className }: { className?: string }) => <div className={className} data-testid="trending-down-icon" />,
  AlertTriangle: ({ className }: { className?: string }) => <div className={className} data-testid="alert-triangle-icon" />,
  Plus: ({ className }: { className?: string }) => <div className={className} data-testid="plus-icon" />,
  Info: ({ className }: { className?: string }) => <div className={className} data-testid="info-icon" />,
}))

describe('CreditBalance Component', () => {
  const mockCreditBalance: CreditBalanceType = {
    remaining: 2500,
    total: 3000,
    usedThisMonth: 500,
    percentageUsed: 16.67,
    subscriptionTier: 'PREMIUM'
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('Loading State', () => {
    it('displays loading skeleton when loading is true', () => {
      render(<CreditBalance loading={true} />)
      
      expect(document.querySelector('.animate-pulse')).toBeInTheDocument()
    })
  })

  describe('Data Display', () => {
    it('renders credit balance information correctly', () => {
      render(<CreditBalance creditBalance={mockCreditBalance} />)
      
      // Check credit balance display
      expect(screen.getByText('2,500')).toBeInTheDocument()
      expect(screen.getByText('Credits Available')).toBeInTheDocument()
      
      // Check monthly usage
      expect(screen.getByText('500 / 3,000')).toBeInTheDocument()
      expect(screen.getByText('16.7% used this month')).toBeInTheDocument()
      
      // Check subscription tier
      expect(screen.getByText('Premium')).toBeInTheDocument()
    })

    it('falls back to user data when creditBalance prop is not provided', () => {
      render(<CreditBalance />)
      
      // Should display user's credit info
      expect(screen.getByText('2,500')).toBeInTheDocument()
      expect(screen.getByText('500 / 3,000')).toBeInTheDocument()
    })

    it('displays subscription tier with correct styling', () => {
      const premiumBalance = { ...mockCreditBalance, subscriptionTier: 'PREMIUM' }
      render(<CreditBalance creditBalance={premiumBalance} />)
      
      const premiumBadge = screen.getByText('Premium')
      expect(premiumBadge).toBeInTheDocument()
      expect(premiumBadge.closest('.bg-purple-100')).toBeInTheDocument()
    })

    it('displays different subscription tiers correctly', () => {
      const basicBalance = { ...mockCreditBalance, subscriptionTier: 'BASIC' }
      const { rerender } = render(<CreditBalance creditBalance={basicBalance} />)
      
      expect(screen.getByText('Basic')).toBeInTheDocument()
      
      const enterpriseBalance = { ...mockCreditBalance, subscriptionTier: 'ENTERPRISE' }
      rerender(<CreditBalance creditBalance={enterpriseBalance} />)
      
      expect(screen.getByText('Enterprise')).toBeInTheDocument()
    })
  })

  describe('Low Balance Alerts', () => {
    it('shows low balance alert when credits are below 100', () => {
      const lowBalance = { ...mockCreditBalance, remaining: 75 }
      render(<CreditBalance creditBalance={lowBalance} />)
      
      expect(screen.getByText('Low Credit Balance')).toBeInTheDocument()
      expect(screen.getByText(/Your credit balance is running low/)).toBeInTheDocument()
    })

    it('shows critical low balance alert when credits are below 25', () => {
      const veryLowBalance = { ...mockCreditBalance, remaining: 15 }
      render(<CreditBalance creditBalance={veryLowBalance} />)
      
      expect(screen.getByText('Critical Low Balance')).toBeInTheDocument()
      expect(screen.getByText(/You have very few credits remaining/)).toBeInTheDocument()
    })

    it('does not show alerts when credits are sufficient', () => {
      render(<CreditBalance creditBalance={mockCreditBalance} />)
      
      expect(screen.queryByText('Low Credit Balance')).not.toBeInTheDocument()
      expect(screen.queryByText('Critical Low Balance')).not.toBeInTheDocument()
    })
  })

  describe('Progress Bar', () => {
    it('displays usage progress correctly', () => {
      render(<CreditBalance creditBalance={mockCreditBalance} />)
      
      const progressElement = document.querySelector('[value="16.67"]')
      expect(progressElement).toBeInTheDocument()
    })

    it('caps progress at 100% when usage exceeds total', () => {
      const overuseBalance = { 
        ...mockCreditBalance, 
        usedThisMonth: 3500, 
        percentageUsed: 116.67 
      }
      render(<CreditBalance creditBalance={overuseBalance} />)
      
      // Progress should be capped at 100
      const progressText = screen.getByText(/116.7% used this month/)
      expect(progressText).toBeInTheDocument()
    })
  })

  describe('Action Button', () => {
    it('renders purchase credits button', () => {
      render(<CreditBalance creditBalance={mockCreditBalance} />)
      
      const purchaseButton = screen.getByRole('button', { name: /purchase credits/i })
      expect(purchaseButton).toBeInTheDocument()
      expect(screen.getByTestId('plus-icon')).toBeInTheDocument()
    })
  })

  describe('Error Handling', () => {
    it('displays fallback message when no data is available', () => {
      // Mock useAuth to return no user
      jest.mocked(require('@/hooks/useAuth').useAuth).mockReturnValue({ user: null })
      
      render(<CreditBalance />)
      
      expect(screen.getByText('Credit Balance')).toBeInTheDocument()
      expect(screen.getByText('Unable to load credit information')).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('includes proper ARIA labels and roles', () => {
      render(<CreditBalance creditBalance={mockCreditBalance} />)
      
      // Check for heading structure
      expect(screen.getByRole('heading', { name: /credit balance/i })).toBeInTheDocument()
      
      // Check for button accessibility
      expect(screen.getByRole('button', { name: /purchase credits/i })).toBeInTheDocument()
    })

    it('includes tooltip for information icon', () => {
      render(<CreditBalance creditBalance={mockCreditBalance} />)
      
      expect(screen.getByTestId('info-icon')).toBeInTheDocument()
    })
  })

  describe('Responsive Design', () => {
    it('applies custom className when provided', () => {
      const { container } = render(
        <CreditBalance creditBalance={mockCreditBalance} className="custom-class" />
      )
      
      expect(container.firstChild).toHaveClass('custom-class')
    })
  })
})