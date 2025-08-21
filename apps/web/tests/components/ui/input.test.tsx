import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'jest-axe'
import { Input } from '@/components/shared/ui/input'

expect.extend(toHaveNoViolations)

describe('Input Component', () => {
  it('renders input element', () => {
    render(<Input />)
    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })

  it('accepts and displays value', () => {
    render(<Input value="test value" onChange={() => {}} />)
    expect(screen.getByRole('textbox')).toHaveValue('test value')
  })

  it('handles onChange events', () => {
    const handleChange = jest.fn()
    render(<Input onChange={handleChange} />)
    const input = screen.getByRole('textbox')
    
    fireEvent.change(input, { target: { value: 'new value' } })
    expect(handleChange).toHaveBeenCalledTimes(1)
  })

  it('supports different input types', () => {
    const { rerender } = render(<Input type="email" />)
    expect(screen.getByRole('textbox')).toHaveAttribute('type', 'email')
    
    rerender(<Input type="password" />)
    const passwordInput = document.querySelector('input[type="password"]')
    expect(passwordInput).toBeInTheDocument()
  })

  it('applies custom className', () => {
    render(<Input className="custom-class" />)
    expect(screen.getByRole('textbox')).toHaveClass('custom-class')
  })

  it('handles disabled state', () => {
    render(<Input disabled />)
    expect(screen.getByRole('textbox')).toBeDisabled()
  })

  it('displays placeholder text', () => {
    render(<Input placeholder="Enter text here" />)
    expect(screen.getByPlaceholderText('Enter text here')).toBeInTheDocument()
  })

  it('forwards ref correctly', () => {
    const ref = React.createRef<HTMLInputElement>()
    render(<Input ref={ref} />)
    expect(ref.current).toBeInstanceOf(HTMLInputElement)
  })

  it('supports required attribute', () => {
    render(<Input required />)
    expect(screen.getByRole('textbox')).toBeRequired()
  })

  it('supports readOnly attribute', () => {
    render(<Input readOnly value="readonly text" />)
    const input = screen.getByRole('textbox')
    expect(input).toHaveAttribute('readOnly')
  })

  describe('Accessibility', () => {
    it('should not have accessibility violations', async () => {
      const { container } = render(
        <div>
          <label htmlFor="test-input">Test Input</label>
          <Input id="test-input" />
        </div>
      )
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })

    it('supports aria-label', () => {
      render(<Input aria-label="Test input field" />)
      expect(screen.getByLabelText('Test input field')).toBeInTheDocument()
    })

    it('supports aria-describedby', () => {
      render(
        <div>
          <Input aria-describedby="input-help" />
          <span id="input-help">Help text</span>
        </div>
      )
      const input = screen.getByRole('textbox')
      expect(input).toHaveAttribute('aria-describedby', 'input-help')
    })

    it('supports aria-invalid for error states', () => {
      render(<Input aria-invalid="true" />)
      expect(screen.getByRole('textbox')).toHaveAttribute('aria-invalid', 'true')
    })

    it('maintains focus visibility', () => {
      render(<Input />)
      const input = screen.getByRole('textbox')
      
      fireEvent.focus(input)
      expect(input).toHaveClass('focus-visible:ring-2')
    })
  })
})