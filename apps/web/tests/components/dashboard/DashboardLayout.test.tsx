/**
 * Tests for Dashboard Layout component
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { useSession } from 'next-auth/react'
import { usePathname } from 'next/navigation'
import DashboardLayout from '@/app/(dashboard)/layout'

// Mock dependencies
jest.mock('next-auth/react')
jest.mock('next/navigation', () => ({
  usePathname: jest.fn(),
}))
jest.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    user: {
      id: '1',
      email: 'test@example.com',
      firstName: 'John',
      lastName: 'Doe',
      companyName: 'Test Company',
      creditsRemaining: 1000,
      creditsUsedThisMonth: 250,
      role: 'USER',
    },
  }),
}))

describe('DashboardLayout', () => {
  beforeEach(() => {
    ;(useSession as jest.Mock).mockReturnValue({
      data: {
        user: {
          email: 'test@example.com',
          name: 'John Doe',
        },
      },
      status: 'authenticated',
    })
    ;(usePathname as jest.Mock).mockReturnValue('/dashboard')
  })

  it('renders the dashboard layout with sidebar navigation', () => {
    render(
      <DashboardLayout>
        <div>Test Content</div>
      </DashboardLayout>
    )

    // Check for navigation items
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Upload Files')).toBeInTheDocument()
    expect(screen.getByText('Processing History')).toBeInTheDocument()
    expect(screen.getByText('Profile')).toBeInTheDocument()
  })

  it('displays user information in header', () => {
    render(
      <DashboardLayout>
        <div>Test Content</div>
      </DashboardLayout>
    )

    // Check for user name and credits
    expect(screen.getByText('John Doe')).toBeInTheDocument()
    expect(screen.getByText('test@example.com')).toBeInTheDocument()
    expect(screen.getByText('1,000')).toBeInTheDocument() // Credits
  })

  it('highlights active navigation item', () => {
    ;(usePathname as jest.Mock).mockReturnValue('/dashboard/upload')
    
    render(
      <DashboardLayout>
        <div>Test Content</div>
      </DashboardLayout>
    )

    const uploadLink = screen.getByRole('link', { name: /upload files/i })
    expect(uploadLink).toHaveClass('bg-blue-50', 'text-blue-700')
  })

  it('toggles mobile sidebar on menu button click', async () => {
    render(
      <DashboardLayout>
        <div>Test Content</div>
      </DashboardLayout>
    )

    // Mobile menu should be hidden initially
    const sidebar = document.querySelector('.lg\\:hidden')
    expect(sidebar).toHaveClass('-translate-x-full')

    // Click menu button to open
    const menuButton = screen.getAllByRole('button')[0]
    fireEvent.click(menuButton)

    await waitFor(() => {
      expect(sidebar).toHaveClass('translate-x-0')
    })
  })

  it('opens user dropdown menu on avatar click', async () => {
    render(
      <DashboardLayout>
        <div>Test Content</div>
      </DashboardLayout>
    )

    // Find and click the user avatar button
    const avatarButton = screen.getByText('JD').closest('button')
    fireEvent.click(avatarButton!)

    await waitFor(() => {
      expect(screen.getByText('Profile Settings')).toBeInTheDocument()
      expect(screen.getByText('Billing & Credits')).toBeInTheDocument()
      expect(screen.getByText('Sign Out')).toBeInTheDocument()
    })
  })

  it('displays company name in user dropdown', async () => {
    render(
      <DashboardLayout>
        <div>Test Content</div>
      </DashboardLayout>
    )

    const avatarButton = screen.getByText('JD').closest('button')
    fireEvent.click(avatarButton!)

    await waitFor(() => {
      expect(screen.getByText('Test Company')).toBeInTheDocument()
    })
  })

  it('renders children content', () => {
    render(
      <DashboardLayout>
        <div data-testid="child-content">Test Child Content</div>
      </DashboardLayout>
    )

    expect(screen.getByTestId('child-content')).toBeInTheDocument()
    expect(screen.getByText('Test Child Content')).toBeInTheDocument()
  })

  it('applies responsive classes for mobile and desktop', () => {
    const { container } = render(
      <DashboardLayout>
        <div>Test Content</div>
      </DashboardLayout>
    )

    // Check for responsive sidebar classes
    const desktopSidebar = container.querySelector('.lg\\:fixed')
    const mobileSidebar = container.querySelector('.lg\\:hidden')

    expect(desktopSidebar).toBeInTheDocument()
    expect(mobileSidebar).toBeInTheDocument()
  })

  it('shows credit balance with proper formatting', () => {
    render(
      <DashboardLayout>
        <div>Test Content</div>
      </DashboardLayout>
    )

    // Check credits display
    expect(screen.getByText('Credits:')).toBeInTheDocument()
    expect(screen.getByText('1,000')).toBeInTheDocument()
  })

  it('handles sign out action', async () => {
    const signOutMock = jest.fn()
    jest.spyOn(require('next-auth/react'), 'signOut').mockImplementation(signOutMock)

    render(
      <DashboardLayout>
        <div>Test Content</div>
      </DashboardLayout>
    )

    // Open dropdown
    const avatarButton = screen.getByText('JD').closest('button')
    fireEvent.click(avatarButton!)

    // Click sign out
    await waitFor(() => {
      const signOutButton = screen.getByText('Sign Out')
      fireEvent.click(signOutButton)
    })

    expect(signOutMock).toHaveBeenCalledWith({ callbackUrl: '/' })
  })
})