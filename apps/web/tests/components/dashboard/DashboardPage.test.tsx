/**
 * Tests for Dashboard Page component
 */
import { render, screen } from '@testing-library/react'
import DashboardPage from '@/app/(dashboard)/dashboard/page'

// Mock dependencies
jest.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    user: {
      id: '1',
      email: 'test@example.com',
      firstName: 'John',
      lastName: 'Doe',
      creditsRemaining: 5000,
      creditsUsedThisMonth: 1250,
      role: 'USER',
    },
  }),
}))

jest.mock('next/link', () => {
  return {
    __esModule: true,
    default: ({ children, href }: { children: React.ReactNode; href: string }) => (
      <a href={href}>{children}</a>
    ),
  }
})

describe('DashboardPage', () => {
  it('renders welcome message with user first name', () => {
    render(<DashboardPage />)
    expect(screen.getByText('Welcome back, John!')).toBeInTheDocument()
  })

  it('displays credit balance information', () => {
    render(<DashboardPage />)
    
    expect(screen.getByText('Credits Remaining')).toBeInTheDocument()
    expect(screen.getByText('5,000')).toBeInTheDocument()
    expect(screen.getByText('1,250 used this month')).toBeInTheDocument()
  })

  it('shows processing statistics cards', () => {
    render(<DashboardPage />)
    
    // Check for statistic cards
    expect(screen.getByText('Total Jobs')).toBeInTheDocument()
    expect(screen.getByText('Success Rate')).toBeInTheDocument()
    expect(screen.getByText('Avg. Confidence')).toBeInTheDocument()
    
    // Check for values
    expect(screen.getByText('127')).toBeInTheDocument()
    expect(screen.getByText('98.5%')).toBeInTheDocument()
    expect(screen.getByText('94.2%')).toBeInTheDocument()
  })

  it('displays quick upload section with link', () => {
    render(<DashboardPage />)
    
    expect(screen.getByText('Quick Upload')).toBeInTheDocument()
    expect(screen.getByText('Start processing your customs declaration files')).toBeInTheDocument()
    
    const uploadButton = screen.getByRole('link', { name: /upload files/i })
    expect(uploadButton).toHaveAttribute('href', '/dashboard/upload')
  })

  it('shows recent processing jobs', () => {
    render(<DashboardPage />)
    
    expect(screen.getByText('Recent Processing Jobs')).toBeInTheDocument()
    
    // Check for job entries
    expect(screen.getByText('import_batch_2024_01.xlsx')).toBeInTheDocument()
    expect(screen.getByText('export_products_jan.csv')).toBeInTheDocument()
    expect(screen.getByText('customs_declaration.xlsx')).toBeInTheDocument()
    
    // Check for status badges
    expect(screen.getAllByText('Completed').length).toBeGreaterThan(0)
    expect(screen.getByText('Processing')).toBeInTheDocument()
  })

  it('displays job details with product count and confidence', () => {
    render(<DashboardPage />)
    
    // Check for product counts
    expect(screen.getByText('150 products')).toBeInTheDocument()
    expect(screen.getByText('87 products')).toBeInTheDocument()
    expect(screen.getByText('234 products')).toBeInTheDocument()
    
    // Check for confidence scores
    expect(screen.getByText('96.5% confidence')).toBeInTheDocument()
    expect(screen.getByText('93.8% confidence')).toBeInTheDocument()
  })

  it('shows processing status breakdown', () => {
    render(<DashboardPage />)
    
    // Pending jobs
    expect(screen.getByText('Pending')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('Jobs in queue')).toBeInTheDocument()
    
    // Completed jobs
    expect(screen.getByText('Completed')).toBeInTheDocument()
    expect(screen.getByText('124')).toBeInTheDocument()
    expect(screen.getByText('Successfully processed')).toBeInTheDocument()
    
    // Failed jobs
    expect(screen.getByText('Failed')).toBeInTheDocument()
    expect(screen.getByText('0')).toBeInTheDocument()
    expect(screen.getByText('Need attention')).toBeInTheDocument()
  })

  it('includes view all link for processing history', () => {
    render(<DashboardPage />)
    
    const viewAllLink = screen.getByRole('link', { name: /view all/i })
    expect(viewAllLink).toHaveAttribute('href', '/dashboard/history')
  })

  it('displays proper status icons for different job states', () => {
    const { container } = render(<DashboardPage />)
    
    // Check for status icons
    const checkCircles = container.querySelectorAll('.text-green-500')
    const alertCircles = container.querySelectorAll('.text-yellow-500')
    
    expect(checkCircles.length).toBeGreaterThan(0)
    expect(alertCircles.length).toBeGreaterThan(0)
  })

  it('shows processing statistics with correct formatting', () => {
    render(<DashboardPage />)
    
    // Check daily processing
    expect(screen.getByText('12 processed today')).toBeInTheDocument()
    
    // Check success stats
    expect(screen.getByText('124 completed successfully')).toBeInTheDocument()
    
    // Check AI accuracy
    expect(screen.getByText('AI matching accuracy')).toBeInTheDocument()
  })
})