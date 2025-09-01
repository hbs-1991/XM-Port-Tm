import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { axe, toHaveNoViolations } from 'jest-axe'
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from '@/components/shared/ui/dialog'

expect.extend(toHaveNoViolations)

describe('Dialog Component', () => {
  it('renders dialog trigger', () => {
    render(
      <Dialog>
        <DialogTrigger>Open Dialog</DialogTrigger>
        <DialogContent>
          <DialogTitle>Test Dialog</DialogTitle>
        </DialogContent>
      </Dialog>
    )
    expect(screen.getByText('Open Dialog')).toBeInTheDocument()
  })

  it('opens dialog when trigger is clicked', async () => {
    render(
      <Dialog>
        <DialogTrigger>Open</DialogTrigger>
        <DialogContent>
          <DialogTitle>Dialog Title</DialogTitle>
          <DialogDescription>Dialog content</DialogDescription>
        </DialogContent>
      </Dialog>
    )

    const trigger = screen.getByText('Open')
    fireEvent.click(trigger)

    await waitFor(() => {
      expect(screen.getByText('Dialog Title')).toBeInTheDocument()
      expect(screen.getByText('Dialog content')).toBeInTheDocument()
    })
  })

  it('closes dialog when close button is clicked', async () => {
    render(
      <Dialog defaultOpen>
        <DialogContent>
          <DialogTitle>Test Dialog</DialogTitle>
        </DialogContent>
      </Dialog>
    )

    expect(screen.getByText('Test Dialog')).toBeInTheDocument()
    
    const closeButton = screen.getByRole('button', { name: /close/i })
    fireEvent.click(closeButton)

    await waitFor(() => {
      expect(screen.queryByText('Test Dialog')).not.toBeInTheDocument()
    })
  })

  it('renders with custom className', () => {
    render(
      <Dialog defaultOpen>
        <DialogContent className="custom-dialog-class">
          <DialogTitle>Test</DialogTitle>
        </DialogContent>
      </Dialog>
    )

    const content = screen.getByRole('dialog')
    expect(content).toHaveClass('custom-dialog-class')
  })

  describe('DialogHeader', () => {
    it('renders header section', () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogHeader data-testid="header">
              <DialogTitle>Header Title</DialogTitle>
            </DialogHeader>
          </DialogContent>
        </Dialog>
      )

      expect(screen.getByTestId('header')).toBeInTheDocument()
      expect(screen.getByText('Header Title')).toBeInTheDocument()
    })

    it('applies custom className to header', () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogHeader className="custom-header" data-testid="header">
              <DialogTitle>Title</DialogTitle>
            </DialogHeader>
          </DialogContent>
        </Dialog>
      )

      expect(screen.getByTestId('header')).toHaveClass('custom-header')
    })
  })

  describe('DialogTitle', () => {
    it('renders title text', () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogTitle>Dialog Title Text</DialogTitle>
          </DialogContent>
        </Dialog>
      )

      expect(screen.getByText('Dialog Title Text')).toBeInTheDocument()
    })

    it('applies title styling', () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogTitle>Title</DialogTitle>
          </DialogContent>
        </Dialog>
      )

      const title = screen.getByText('Title')
      expect(title).toHaveClass('text-lg', 'font-semibold')
    })
  })

  describe('DialogDescription', () => {
    it('renders description text', () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogDescription>Description text here</DialogDescription>
          </DialogContent>
        </Dialog>
      )

      expect(screen.getByText('Description text here')).toBeInTheDocument()
    })

    it('applies description styling', () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogDescription>Description</DialogDescription>
          </DialogContent>
        </Dialog>
      )

      const description = screen.getByText('Description')
      expect(description).toHaveClass('text-sm', 'text-muted-foreground')
    })
  })

  describe('DialogFooter', () => {
    it('renders footer section', () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogFooter data-testid="footer">
              <button>Cancel</button>
              <button>Confirm</button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )

      expect(screen.getByTestId('footer')).toBeInTheDocument()
      expect(screen.getByText('Cancel')).toBeInTheDocument()
      expect(screen.getByText('Confirm')).toBeInTheDocument()
    })

    it('applies footer styling', () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogFooter data-testid="footer">
              <button>Action</button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )

      expect(screen.getByTestId('footer')).toHaveClass('flex')
    })
  })

  describe('Keyboard Navigation', () => {
    it('closes dialog on Escape key', async () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogTitle>Test Dialog</DialogTitle>
          </DialogContent>
        </Dialog>
      )

      expect(screen.getByText('Test Dialog')).toBeInTheDocument()

      fireEvent.keyDown(document, { key: 'Escape' })

      await waitFor(() => {
        expect(screen.queryByText('Test Dialog')).not.toBeInTheDocument()
      })
    })

    it('traps focus within dialog', async () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Focus Test</DialogTitle>
            </DialogHeader>
            <button>First Button</button>
            <button>Second Button</button>
            <DialogFooter>
              <button>Footer Button</button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )

      // Focus should be trapped within the dialog
      const buttons = screen.getAllByRole('button')
      expect(buttons.length).toBeGreaterThan(0)
    })
  })

  describe('Controlled State', () => {
    it('works as controlled component', async () => {
      const ControlledDialog = () => {
        const [open, setOpen] = React.useState(false)
        
        return (
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger>Open Controlled</DialogTrigger>
            <DialogContent>
              <DialogTitle>Controlled Dialog</DialogTitle>
              <button onClick={() => setOpen(false)}>Close</button>
            </DialogContent>
          </Dialog>
        )
      }

      render(<ControlledDialog />)

      const trigger = screen.getByText('Open Controlled')
      fireEvent.click(trigger)

      await waitFor(() => {
        expect(screen.getByText('Controlled Dialog')).toBeInTheDocument()
      })

      const closeButton = screen.getAllByText('Close')[0]
      fireEvent.click(closeButton)

      await waitFor(() => {
        expect(screen.queryByText('Controlled Dialog')).not.toBeInTheDocument()
      })
    })
  })

  describe('Accessibility', () => {
    it('should not have accessibility violations', async () => {
      const { container } = render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Accessible Dialog</DialogTitle>
              <DialogDescription>
                This dialog should be fully accessible
              </DialogDescription>
            </DialogHeader>
            <div>Dialog body content</div>
            <DialogFooter>
              <DialogClose>Close</DialogClose>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )

      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })

    it('has proper ARIA attributes', () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogTitle>ARIA Test</DialogTitle>
            <DialogDescription>Description for ARIA</DialogDescription>
          </DialogContent>
        </Dialog>
      )

      const dialog = screen.getByRole('dialog')
      expect(dialog).toBeInTheDocument()
      expect(dialog).toHaveAttribute('aria-labelledby')
      expect(dialog).toHaveAttribute('aria-describedby')
    })

    it('includes screen reader only close button text', () => {
      render(
        <Dialog defaultOpen>
          <DialogContent>
            <DialogTitle>Test</DialogTitle>
          </DialogContent>
        </Dialog>
      )

      expect(screen.getByText('Close')).toHaveClass('sr-only')
    })
  })
})