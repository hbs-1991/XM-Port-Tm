/**
 * @jest-environment jsdom
 */

import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { useRouter } from 'next/navigation'
import ProfilePage from '@/app/dashboard/profile/page'
import { useAuth } from '@/hooks/useAuth'
import { toast } from '@/components/shared/ui/use-toast'

// Mock dependencies
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}))

jest.mock('@/hooks/useAuth', () => ({
  useAuth: jest.fn(),
}))

jest.mock('@/components/shared/ui/use-toast', () => ({
  toast: jest.fn(),
}))

// Mock fetch
global.fetch = jest.fn()

const mockRouter = {
  push: jest.fn(),
}

const mockUser = {
  id: '1',
  email: 'test@example.com',
  firstName: 'John',
  lastName: 'Doe',
  companyName: 'Test Company',
  country: 'USA',
  role: 'USER',
  creditsRemaining: 1000,
  isActive: true,
}

const mockUseAuth = {
  user: mockUser,
  isLoading: false,
  logoutAll: jest.fn(),
  refreshUser: jest.fn(),
}

describe('ProfilePage', () => {
  beforeEach(() => {
    ;(useRouter as jest.Mock).mockReturnValue(mockRouter)
    ;(useAuth as jest.Mock).mockReturnValue(mockUseAuth)
    ;(fetch as jest.Mock).mockClear()
    ;(toast as jest.Mock).mockClear()
  })

  afterEach(() => {
    jest.clearAllMocks()
  })

  it('renders profile information correctly', () => {
    render(<ProfilePage />)

    expect(screen.getByText('Profile Settings')).toBeInTheDocument()
    expect(screen.getByText('John')).toBeInTheDocument()
    expect(screen.getByText('Doe')).toBeInTheDocument()
    expect(screen.getByText('test@example.com')).toBeInTheDocument()
    expect(screen.getByText('Test Company')).toBeInTheDocument()
    expect(screen.getByText('USA')).toBeInTheDocument()
    expect(screen.getByText('1,000')).toBeInTheDocument()
  })

  it('enters edit mode when edit button is clicked', async () => {
    render(<ProfilePage />)

    const editButton = screen.getByText('Edit Profile')
    fireEvent.click(editButton)

    await waitFor(() => {
      expect(screen.getByDisplayValue('John')).toBeInTheDocument()
      expect(screen.getByDisplayValue('Doe')).toBeInTheDocument()
      expect(screen.getByDisplayValue('Test Company')).toBeInTheDocument()
      expect(screen.getByDisplayValue('USA')).toBeInTheDocument()
    })

    expect(screen.getByText('Save Changes')).toBeInTheDocument()
    expect(screen.getByText('Cancel')).toBeInTheDocument()
  })

  it('cancels editing and reverts changes', async () => {
    render(<ProfilePage />)

    // Enter edit mode
    const editButton = screen.getByText('Edit Profile')
    fireEvent.click(editButton)

    await waitFor(() => {
      expect(screen.getByDisplayValue('John')).toBeInTheDocument()
    })

    // Make changes
    const firstNameInput = screen.getByDisplayValue('John')
    fireEvent.change(firstNameInput, { target: { value: 'Jane' } })

    expect(screen.getByDisplayValue('Jane')).toBeInTheDocument()

    // Cancel changes
    const cancelButton = screen.getByText('Cancel')
    fireEvent.click(cancelButton)

    await waitFor(() => {
      expect(screen.getByText('John')).toBeInTheDocument()
      expect(screen.queryByDisplayValue('Jane')).not.toBeInTheDocument()
    })
  })

  it('saves profile changes successfully', async () => {
    ;(fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        id: '1',
        firstName: 'Jane',
        lastName: 'Doe',
        companyName: 'Test Company',
        country: 'USA',
      }),
    })

    render(<ProfilePage />)

    // Enter edit mode
    const editButton = screen.getByText('Edit Profile')
    fireEvent.click(editButton)

    await waitFor(() => {
      expect(screen.getByDisplayValue('John')).toBeInTheDocument()
    })

    // Make changes
    const firstNameInput = screen.getByDisplayValue('John')
    fireEvent.change(firstNameInput, { target: { value: 'Jane' } })

    // Save changes
    const saveButton = screen.getByText('Save Changes')
    fireEvent.click(saveButton)

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith('/api/proxy/users/profile', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          firstName: 'Jane',
        }),
      })
    })

    expect(mockUseAuth.refreshUser).toHaveBeenCalled()
    expect(toast).toHaveBeenCalledWith({
      title: 'Profile Updated',
      description: 'Your profile information has been successfully updated.',
    })
  })

  it('handles save profile error', async () => {
    ;(fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'))

    render(<ProfilePage />)

    // Enter edit mode
    const editButton = screen.getByText('Edit Profile')
    fireEvent.click(editButton)

    await waitFor(() => {
      expect(screen.getByDisplayValue('John')).toBeInTheDocument()
    })

    // Make changes
    const firstNameInput = screen.getByDisplayValue('John')
    fireEvent.change(firstNameInput, { target: { value: 'Jane' } })

    // Save changes
    const saveButton = screen.getByText('Save Changes')
    fireEvent.click(saveButton)

    await waitFor(() => {
      expect(toast).toHaveBeenCalledWith({
        title: 'Update Failed',
        description: 'Failed to update your profile. Please try again.',
        variant: 'destructive',
      })
    })
  })

  it('disables save button when no changes are made', async () => {
    render(<ProfilePage />)

    // Enter edit mode
    const editButton = screen.getByText('Edit Profile')
    fireEvent.click(editButton)

    await waitFor(() => {
      const saveButton = screen.getByText('Save Changes')
      expect(saveButton).toBeDisabled()
    })
  })

  it('shows unsaved changes warning', async () => {
    render(<ProfilePage />)

    // Enter edit mode
    const editButton = screen.getByText('Edit Profile')
    fireEvent.click(editButton)

    await waitFor(() => {
      expect(screen.getByDisplayValue('John')).toBeInTheDocument()
    })

    // Make changes
    const firstNameInput = screen.getByDisplayValue('John')
    fireEvent.change(firstNameInput, { target: { value: 'Jane' } })

    await waitFor(() => {
      expect(screen.getByText('You have unsaved changes. Click "Save Changes" to update your profile.')).toBeInTheDocument()
    })
  })

  it('handles logout all devices', async () => {
    mockUseAuth.logoutAll.mockResolvedValueOnce(undefined)

    render(<ProfilePage />)

    const logoutAllButton = screen.getByText('Sign Out All')
    fireEvent.click(logoutAllButton)

    await waitFor(() => {
      expect(mockUseAuth.logoutAll).toHaveBeenCalled()
      expect(mockRouter.push).toHaveBeenCalledWith('/')
    })
  })

  it('shows loading state during save', async () => {
    ;(fetch as jest.Mock).mockImplementationOnce(
      () =>
        new Promise((resolve) =>
          setTimeout(() => resolve({ ok: true, json: () => ({}) }), 100)
        )
    )

    render(<ProfilePage />)

    // Enter edit mode
    const editButton = screen.getByText('Edit Profile')
    fireEvent.click(editButton)

    await waitFor(() => {
      expect(screen.getByDisplayValue('John')).toBeInTheDocument()
    })

    // Make changes
    const firstNameInput = screen.getByDisplayValue('John')
    fireEvent.change(firstNameInput, { target: { value: 'Jane' } })

    // Save changes
    const saveButton = screen.getByText('Save Changes')
    fireEvent.click(saveButton)

    // Should show loading state
    await waitFor(() => {
      expect(screen.getByText('Saving...')).toBeInTheDocument()
    })
  })

  it('shows button is disabled when no changes are made', async () => {
    render(<ProfilePage />)

    // Enter edit mode
    const editButton = screen.getByText('Edit Profile')
    fireEvent.click(editButton)

    await waitFor(() => {
      const saveButton = screen.getByText('Save Changes')
      expect(saveButton).toBeDisabled()
    })

    // Make a change then revert it to original values
    const firstNameInput = screen.getByDisplayValue('John')
    fireEvent.change(firstNameInput, { target: { value: 'Jane' } })
    
    // Now the save button should be enabled
    await waitFor(() => {
      const saveButton = screen.getByText('Save Changes')
      expect(saveButton).not.toBeDisabled()
    })
    
    // Revert the change back to original
    fireEvent.change(firstNameInput, { target: { value: 'John' } })

    // Button should be disabled again since no changes from original
    await waitFor(() => {
      const saveButton = screen.getByText('Save Changes')
      expect(saveButton).toBeDisabled()
    })
  })
})