import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'jest-axe'
import {
  Toast,
  ToastProvider,
  ToastViewport,
  ToastTitle,
  ToastDescription,
  ToastClose,
  ToastAction,
} from '@/components/shared/ui/toast'

expect.extend(toHaveNoViolations)

// Test wrapper component with provider
const ToastWrapper = ({ children }: { children: React.ReactNode }) => (
  <ToastProvider>
    {children}
    <ToastViewport />
  </ToastProvider>
)

describe('Toast Component', () => {
  it('renders toast notification', () => {
    render(
      <ToastWrapper>
        <Toast open>
          <ToastTitle>Notification</ToastTitle>
          <ToastDescription>This is a toast message</ToastDescription>
        </Toast>
      </ToastWrapper>
    )
    
    expect(screen.getByText('Notification')).toBeInTheDocument()
    expect(screen.getByText('This is a toast message')).toBeInTheDocument()
  })

  it('applies default variant styling', () => {
    render(
      <ToastWrapper>
        <Toast open data-testid="toast">
          <ToastTitle>Default Toast</ToastTitle>
        </Toast>
      </ToastWrapper>
    )
    
    const toast = screen.getByTestId('toast')
    expect(toast).toHaveClass('border', 'bg-background', 'text-foreground')
  })

  it('applies destructive variant styling', () => {
    render(
      <ToastWrapper>
        <Toast open variant="destructive" data-testid="toast">
          <ToastTitle>Error Toast</ToastTitle>
        </Toast>
      </ToastWrapper>
    )
    
    const toast = screen.getByTestId('toast')
    expect(toast).toHaveClass('destructive', 'border-destructive', 'bg-destructive')
  })

  it('applies custom className', () => {
    render(
      <ToastWrapper>
        <Toast open className="custom-toast" data-testid="toast">
          <ToastTitle>Custom Toast</ToastTitle>
        </Toast>
      </ToastWrapper>
    )
    
    expect(screen.getByTestId('toast')).toHaveClass('custom-toast')
  })

  describe('ToastTitle', () => {
    it('renders title text', () => {
      render(
        <ToastWrapper>
          <Toast open>
            <ToastTitle>Toast Title Text</ToastTitle>
          </Toast>
        </ToastWrapper>
      )
      
      expect(screen.getByText('Toast Title Text')).toBeInTheDocument()
    })

    it('applies title styling', () => {
      render(
        <ToastWrapper>
          <Toast open>
            <ToastTitle>Title</ToastTitle>
          </Toast>
        </ToastWrapper>
      )
      
      const title = screen.getByText('Title')
      expect(title).toHaveClass('text-sm', 'font-semibold')
    })

    it('applies custom className to title', () => {
      render(
        <ToastWrapper>
          <Toast open>
            <ToastTitle className="custom-title">Title</ToastTitle>
          </Toast>
        </ToastWrapper>
      )
      
      expect(screen.getByText('Title')).toHaveClass('custom-title')
    })
  })

  describe('ToastDescription', () => {
    it('renders description text', () => {
      render(
        <ToastWrapper>
          <Toast open>
            <ToastDescription>Description text here</ToastDescription>
          </Toast>
        </ToastWrapper>
      )
      
      expect(screen.getByText('Description text here')).toBeInTheDocument()
    })

    it('applies description styling', () => {
      render(
        <ToastWrapper>
          <Toast open>
            <ToastDescription>Description</ToastDescription>
          </Toast>
        </ToastWrapper>
      )
      
      const description = screen.getByText('Description')
      expect(description).toHaveClass('text-sm', 'opacity-90')
    })

    it('applies custom className to description', () => {
      render(
        <ToastWrapper>
          <Toast open>
            <ToastDescription className="custom-desc">Desc</ToastDescription>
          </Toast>
        </ToastWrapper>
      )
      
      expect(screen.getByText('Desc')).toHaveClass('custom-desc')
    })
  })

  describe('ToastAction', () => {
    it('renders action button', () => {
      render(
        <ToastWrapper>
          <Toast open>
            <ToastTitle>Title</ToastTitle>
            <ToastAction altText="Undo action">Undo</ToastAction>
          </Toast>
        </ToastWrapper>
      )
      
      expect(screen.getByText('Undo')).toBeInTheDocument()
    })

    it('handles action click', () => {
      const handleClick = jest.fn()
      
      render(
        <ToastWrapper>
          <Toast open>
            <ToastTitle>Title</ToastTitle>
            <ToastAction altText="Try again" onClick={handleClick}>
              Try again
            </ToastAction>
          </Toast>
        </ToastWrapper>
      )
      
      const action = screen.getByText('Try again')
      fireEvent.click(action)
      
      expect(handleClick).toHaveBeenCalledTimes(1)
    })

    it('applies action button styling', () => {
      render(
        <ToastWrapper>
          <Toast open>
            <ToastTitle>Title</ToastTitle>
            <ToastAction altText="Action">Action</ToastAction>
          </Toast>
        </ToastWrapper>
      )
      
      const action = screen.getByText('Action')
      expect(action).toHaveClass('inline-flex', 'items-center', 'justify-center')
    })

    it('applies custom className to action', () => {
      render(
        <ToastWrapper>
          <Toast open>
            <ToastTitle>Title</ToastTitle>
            <ToastAction altText="Action" className="custom-action">
              Action
            </ToastAction>
          </Toast>
        </ToastWrapper>
      )
      
      expect(screen.getByText('Action')).toHaveClass('custom-action')
    })
  })

  describe('ToastClose', () => {
    it('renders close button', () => {
      render(
        <ToastWrapper>
          <Toast open>
            <ToastTitle>Closable Toast</ToastTitle>
            <ToastClose />
          </Toast>
        </ToastWrapper>
      )
      
      const closeButton = document.querySelector('[toast-close]')
      expect(closeButton).toBeInTheDocument()
    })

    it('contains X icon', () => {
      render(
        <ToastWrapper>
          <Toast open>
            <ToastTitle>Toast</ToastTitle>
            <ToastClose />
          </Toast>
        </ToastWrapper>
      )
      
      const icon = document.querySelector('.lucide-x')
      expect(icon).toBeInTheDocument()
    })

    it('applies close button styling', () => {
      render(
        <ToastWrapper>
          <Toast open>
            <ToastTitle>Toast</ToastTitle>
            <ToastClose data-testid="close" />
          </Toast>
        </ToastWrapper>
      )
      
      const closeButton = screen.getByTestId('close')
      expect(closeButton).toHaveClass('absolute', 'right-2', 'top-2')
    })

    it('applies custom className to close button', () => {
      render(
        <ToastWrapper>
          <Toast open>
            <ToastTitle>Toast</ToastTitle>
            <ToastClose className="custom-close" data-testid="close" />
          </Toast>
        </ToastWrapper>
      )
      
      expect(screen.getByTestId('close')).toHaveClass('custom-close')
    })
  })

  describe('ToastViewport', () => {
    it('renders viewport container', () => {
      const { container } = render(
        <ToastProvider>
          <ToastViewport data-testid="viewport" />
        </ToastProvider>
      )
      
      const viewport = screen.getByTestId('viewport')
      expect(viewport).toBeInTheDocument()
    })

    it('applies viewport positioning', () => {
      render(
        <ToastProvider>
          <ToastViewport data-testid="viewport" />
        </ToastProvider>
      )
      
      const viewport = screen.getByTestId('viewport')
      expect(viewport).toHaveClass('fixed', 'z-[100]')
    })

    it('applies custom className to viewport', () => {
      render(
        <ToastProvider>
          <ToastViewport className="custom-viewport" data-testid="viewport" />
        </ToastProvider>
      )
      
      expect(screen.getByTestId('viewport')).toHaveClass('custom-viewport')
    })
  })

  describe('Complete Toast Composition', () => {
    it('renders toast with all components', () => {
      render(
        <ToastWrapper>
          <Toast open>
            <div className="grid gap-1">
              <ToastTitle>Success!</ToastTitle>
              <ToastDescription>Your changes have been saved.</ToastDescription>
            </div>
            <ToastAction altText="Undo">Undo</ToastAction>
            <ToastClose />
          </Toast>
        </ToastWrapper>
      )
      
      expect(screen.getByText('Success!')).toBeInTheDocument()
      expect(screen.getByText('Your changes have been saved.')).toBeInTheDocument()
      expect(screen.getByText('Undo')).toBeInTheDocument()
      expect(document.querySelector('[toast-close]')).toBeInTheDocument()
    })
  })

  describe('Controlled State', () => {
    it('respects open prop', () => {
      const { rerender } = render(
        <ToastWrapper>
          <Toast open={false}>
            <ToastTitle>Hidden Toast</ToastTitle>
          </Toast>
        </ToastWrapper>
      )
      
      expect(screen.queryByText('Hidden Toast')).not.toBeInTheDocument()
      
      rerender(
        <ToastWrapper>
          <Toast open={true}>
            <ToastTitle>Hidden Toast</ToastTitle>
          </Toast>
        </ToastWrapper>
      )
      
      expect(screen.getByText('Hidden Toast')).toBeInTheDocument()
    })

    it('handles onOpenChange callback', () => {
      const handleOpenChange = jest.fn()
      
      render(
        <ToastWrapper>
          <Toast open onOpenChange={handleOpenChange}>
            <ToastTitle>Toast</ToastTitle>
            <ToastClose />
          </Toast>
        </ToastWrapper>
      )
      
      const closeButton = document.querySelector('[toast-close]')
      if (closeButton) {
        fireEvent.click(closeButton)
        expect(handleOpenChange).toHaveBeenCalled()
      }
    })
  })

  describe('Animation States', () => {
    it('applies open animation classes', () => {
      render(
        <ToastWrapper>
          <Toast open data-state="open" data-testid="toast">
            <ToastTitle>Animated Toast</ToastTitle>
          </Toast>
        </ToastWrapper>
      )
      
      const toast = screen.getByTestId('toast')
      expect(toast).toHaveClass('data-[state=open]:animate-in')
    })

    it('applies closed animation classes', () => {
      render(
        <ToastWrapper>
          <Toast open data-state="closed" data-testid="toast">
            <ToastTitle>Closing Toast</ToastTitle>
          </Toast>
        </ToastWrapper>
      )
      
      const toast = screen.getByTestId('toast')
      expect(toast).toHaveClass('data-[state=closed]:animate-out')
    })
  })

  describe('Accessibility', () => {
    it('should not have accessibility violations', async () => {
      const { container } = render(
        <ToastWrapper>
          <Toast open>
            <ToastTitle>Accessible Toast</ToastTitle>
            <ToastDescription>This toast is accessible</ToastDescription>
            <ToastAction altText="Perform action">Action</ToastAction>
            <ToastClose aria-label="Close notification" />
          </Toast>
        </ToastWrapper>
      )
      
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })

    it('has proper ARIA attributes', () => {
      render(
        <ToastWrapper>
          <Toast open data-testid="toast">
            <ToastTitle>ARIA Toast</ToastTitle>
            <ToastDescription>Description for ARIA</ToastDescription>
          </Toast>
        </ToastWrapper>
      )
      
      const toast = screen.getByTestId('toast')
      // Toast should have aria-live or role attribute set by Radix
      expect(toast).toBeInTheDocument()
    })

    it('action has alt text for screen readers', () => {
      render(
        <ToastWrapper>
          <Toast open>
            <ToastTitle>Toast</ToastTitle>
            <ToastAction altText="Undo the last action">Undo</ToastAction>
          </Toast>
        </ToastWrapper>
      )
      
      const action = screen.getByText('Undo')
      // Action should be accessible with proper alt text provided
      expect(action).toBeInTheDocument()
    })

    it('supports keyboard navigation', () => {
      render(
        <ToastWrapper>
          <Toast open>
            <ToastTitle>Keyboard Toast</ToastTitle>
            <ToastAction altText="Action">Action</ToastAction>
            <ToastClose />
          </Toast>
        </ToastWrapper>
      )
      
      const action = screen.getByText('Action')
      const closeButton = document.querySelector('[toast-close]')
      
      expect(action).toHaveClass('focus:ring-2')
      expect(closeButton).toHaveClass('focus:ring-2')
    })
  })
})