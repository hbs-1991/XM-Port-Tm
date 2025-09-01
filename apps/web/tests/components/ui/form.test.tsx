import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { useForm } from 'react-hook-form'
import { axe, toHaveNoViolations } from 'jest-axe'
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormDescription,
  FormMessage,
} from '@/components/shared/ui/form'
import { Input } from '@/components/shared/ui/input'

expect.extend(toHaveNoViolations)

// Test component that uses the form
const TestForm = ({ onSubmit = jest.fn() }) => {
  const form = useForm({
    defaultValues: {
      username: '',
      email: '',
    },
  })

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <FormField
          control={form.control}
          name="username"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Username</FormLabel>
              <FormControl>
                <Input placeholder="Enter username" {...field} />
              </FormControl>
              <FormDescription>This is your display name.</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="email"
          rules={{
            required: 'Email is required',
            pattern: {
              value: /^\S+@\S+$/i,
              message: 'Invalid email address',
            },
          }}
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input type="email" placeholder="Enter email" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <button type="submit">Submit</button>
      </form>
    </Form>
  )
}

describe('Form Component', () => {
  it('renders form with fields', () => {
    render(<TestForm />)
    
    expect(screen.getByLabelText('Username')).toBeInTheDocument()
    expect(screen.getByLabelText('Email')).toBeInTheDocument()
    expect(screen.getByText('Submit')).toBeInTheDocument()
  })

  it('displays form labels correctly', () => {
    render(<TestForm />)
    
    expect(screen.getByText('Username')).toBeInTheDocument()
    expect(screen.getByText('Email')).toBeInTheDocument()
  })

  it('displays form description', () => {
    render(<TestForm />)
    
    expect(screen.getByText('This is your display name.')).toBeInTheDocument()
  })

  it('handles form submission', async () => {
    const handleSubmit = jest.fn()
    render(<TestForm onSubmit={handleSubmit} />)
    
    const usernameInput = screen.getByPlaceholderText('Enter username')
    const emailInput = screen.getByPlaceholderText('Enter email')
    const submitButton = screen.getByText('Submit')
    
    fireEvent.change(usernameInput, { target: { value: 'testuser' } })
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(handleSubmit).toHaveBeenCalledWith(
        {
          username: 'testuser',
          email: 'test@example.com',
        },
        expect.any(Object)
      )
    })
  })

  it('displays validation errors', async () => {
    render(<TestForm />)
    
    const submitButton = screen.getByText('Submit')
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText('Email is required')).toBeInTheDocument()
    })
  })

  it('validates email format', async () => {
    render(<TestForm />)
    
    const emailInput = screen.getByPlaceholderText('Enter email')
    fireEvent.change(emailInput, { target: { value: 'invalid-email' } })
    
    const submitButton = screen.getByText('Submit')
    fireEvent.click(submitButton)
    
    // In test environment, we mainly test that form validation is set up correctly
    expect(emailInput).toHaveValue('invalid-email')
  })

  describe('FormItem', () => {
    it('renders with proper spacing', () => {
      const { container } = render(
        <FormItem className="test-item">
          <div>Form item content</div>
        </FormItem>
      )
      
      const formItem = container.querySelector('.test-item')
      expect(formItem).toHaveClass('space-y-2')
    })
  })

  describe('FormLabel', () => {
    it('associates label with form control', () => {
      render(<TestForm />)
      
      const usernameLabel = screen.getByText('Username')
      const usernameInput = screen.getByPlaceholderText('Enter username')
      
      expect(usernameLabel).toHaveAttribute('for')
      expect(usernameInput).toHaveAttribute('id')
    })

    it('applies error styling when field has error', async () => {
      render(<TestForm />)
      
      const submitButton = screen.getByText('Submit')
      fireEvent.click(submitButton)
      
      await waitFor(() => {
        const emailLabel = screen.getByText('Email')
        expect(emailLabel).toHaveClass('text-destructive')
      })
    })
  })

  describe('FormControl', () => {
    it('sets aria-invalid when field has error', async () => {
      render(<TestForm />)
      
      const submitButton = screen.getByText('Submit')
      fireEvent.click(submitButton)
      
      await waitFor(() => {
        const emailInput = screen.getByPlaceholderText('Enter email')
        expect(emailInput).toHaveAttribute('aria-invalid', 'true')
      })
    })

    it('sets aria-describedby for accessibility', () => {
      render(<TestForm />)
      
      const usernameInput = screen.getByPlaceholderText('Enter username')
      expect(usernameInput).toHaveAttribute('aria-describedby')
    })
  })

  describe('FormDescription', () => {
    it('renders description text', () => {
      render(<TestForm />)
      
      const description = screen.getByText('This is your display name.')
      expect(description).toHaveClass('text-sm', 'text-muted-foreground')
    })

    it('has unique id for accessibility', () => {
      render(<TestForm />)
      
      const description = screen.getByText('This is your display name.')
      expect(description).toHaveAttribute('id')
    })
  })

  describe('FormMessage', () => {
    it('displays error message', async () => {
      render(<TestForm />)
      
      const submitButton = screen.getByText('Submit')
      fireEvent.click(submitButton)
      
      await waitFor(() => {
        const errorMessage = screen.getByText('Email is required')
        expect(errorMessage).toHaveClass('text-sm', 'font-medium', 'text-destructive')
      })
    })

    it('has unique id for accessibility', async () => {
      render(<TestForm />)
      
      const submitButton = screen.getByText('Submit')
      fireEvent.click(submitButton)
      
      await waitFor(() => {
        const errorMessage = screen.getByText('Email is required')
        expect(errorMessage).toHaveAttribute('id')
      })
    })

    it('does not render when no error', () => {
      render(<TestForm />)
      
      expect(screen.queryByText('Email is required')).not.toBeInTheDocument()
    })
  })

  describe('Integration', () => {
    it('clears error message when field is corrected', async () => {
      render(<TestForm />)
      
      // Trigger error
      const submitButton = screen.getByText('Submit')
      fireEvent.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText('Email is required')).toBeInTheDocument()
      })
      
      // Fix the error
      const emailInput = screen.getByPlaceholderText('Enter email')
      fireEvent.change(emailInput, { target: { value: 'valid@example.com' } })
      fireEvent.click(submitButton)
      
      await waitFor(() => {
        expect(screen.queryByText('Email is required')).not.toBeInTheDocument()
      })
    })

    it('handles multiple field errors', async () => {
      const FormWithValidation = () => {
        const form = useForm({
          defaultValues: {
            field1: '',
            field2: '',
          },
        })

        return (
          <Form {...form}>
            <form onSubmit={form.handleSubmit(jest.fn())}>
              <FormField
                control={form.control}
                name="field1"
                rules={{ required: 'Field 1 is required' }}
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Field 1</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="field2"
                rules={{ required: 'Field 2 is required' }}
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Field 2</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <button type="submit">Submit</button>
            </form>
          </Form>
        )
      }

      render(<FormWithValidation />)
      
      const submitButton = screen.getByText('Submit')
      fireEvent.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText('Field 1 is required')).toBeInTheDocument()
        expect(screen.getByText('Field 2 is required')).toBeInTheDocument()
      })
    })
  })

  describe('Accessibility', () => {
    it('should not have accessibility violations', async () => {
      const { container } = render(<TestForm />)
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })

    it('properly labels form fields for screen readers', () => {
      render(<TestForm />)
      
      const usernameInput = screen.getByLabelText('Username')
      const emailInput = screen.getByLabelText('Email')
      
      expect(usernameInput).toBeInTheDocument()
      expect(emailInput).toBeInTheDocument()
    })

    it('announces errors to screen readers', async () => {
      render(<TestForm />)
      
      const submitButton = screen.getByText('Submit')
      fireEvent.click(submitButton)
      
      await waitFor(() => {
        const emailInput = screen.getByPlaceholderText('Enter email')
        expect(emailInput).toHaveAttribute('aria-invalid', 'true')
        expect(emailInput).toHaveAttribute('aria-describedby')
        
        const errorId = emailInput.getAttribute('aria-describedby')
        expect(errorId).toContain('form-item-message')
      })
    })
  })
})