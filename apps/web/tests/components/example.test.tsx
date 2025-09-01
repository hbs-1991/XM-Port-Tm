/**
 * Example component tests
 */
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from '@jest/globals'

// Example Button component test
describe('Button Component', () => {
  it('renders a button with text', () => {
    const ButtonComponent = ({ children }: { children: React.ReactNode }) => (
      <button>{children}</button>
    )
    
    render(<ButtonComponent>Click me</ButtonComponent>)
    
    const button = screen.getByRole('button', { name: /click me/i })
    expect(button).toBeInTheDocument()
  })
})