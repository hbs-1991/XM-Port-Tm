import React from 'react'
import { render, screen } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'jest-axe'
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from '@/components/shared/ui/card'

expect.extend(toHaveNoViolations)

describe('Card Component', () => {
  it('renders card container', () => {
    render(<Card data-testid="card">Card content</Card>)
    const card = screen.getByTestId('card')
    expect(card).toBeInTheDocument()
    expect(card).toHaveTextContent('Card content')
  })

  it('applies custom className to Card', () => {
    render(<Card data-testid="card" className="custom-card-class">Content</Card>)
    expect(screen.getByTestId('card')).toHaveClass('custom-card-class')
  })

  it('forwards ref to Card correctly', () => {
    const ref = React.createRef<HTMLDivElement>()
    render(<Card ref={ref}>Content</Card>)
    expect(ref.current).toBeInstanceOf(HTMLDivElement)
  })

  describe('CardHeader', () => {
    it('renders header section', () => {
      render(
        <Card>
          <CardHeader data-testid="header">Header content</CardHeader>
        </Card>
      )
      const header = screen.getByTestId('header')
      expect(header).toBeInTheDocument()
      expect(header).toHaveTextContent('Header content')
    })

    it('applies custom className to CardHeader', () => {
      render(
        <CardHeader data-testid="header" className="custom-header">
          Header
        </CardHeader>
      )
      expect(screen.getByTestId('header')).toHaveClass('custom-header')
    })
  })

  describe('CardTitle', () => {
    it('renders title text', () => {
      render(<CardTitle>Card Title</CardTitle>)
      expect(screen.getByText('Card Title')).toBeInTheDocument()
    })

    it('applies title styling', () => {
      render(<CardTitle data-testid="title">Title</CardTitle>)
      expect(screen.getByTestId('title')).toHaveClass('text-2xl', 'font-semibold')
    })

    it('applies custom className to CardTitle', () => {
      render(
        <CardTitle data-testid="title" className="custom-title">
          Title
        </CardTitle>
      )
      expect(screen.getByTestId('title')).toHaveClass('custom-title')
    })
  })

  describe('CardDescription', () => {
    it('renders description text', () => {
      render(<CardDescription>Card description text</CardDescription>)
      expect(screen.getByText('Card description text')).toBeInTheDocument()
    })

    it('applies description styling', () => {
      render(<CardDescription data-testid="desc">Description</CardDescription>)
      expect(screen.getByTestId('desc')).toHaveClass('text-sm', 'text-muted-foreground')
    })

    it('applies custom className to CardDescription', () => {
      render(
        <CardDescription data-testid="desc" className="custom-desc">
          Description
        </CardDescription>
      )
      expect(screen.getByTestId('desc')).toHaveClass('custom-desc')
    })
  })

  describe('CardContent', () => {
    it('renders content section', () => {
      render(
        <Card>
          <CardContent data-testid="content">Main content</CardContent>
        </Card>
      )
      const content = screen.getByTestId('content')
      expect(content).toBeInTheDocument()
      expect(content).toHaveTextContent('Main content')
    })

    it('applies content padding', () => {
      render(<CardContent data-testid="content">Content</CardContent>)
      expect(screen.getByTestId('content')).toHaveClass('p-6', 'pt-0')
    })

    it('applies custom className to CardContent', () => {
      render(
        <CardContent data-testid="content" className="custom-content">
          Content
        </CardContent>
      )
      expect(screen.getByTestId('content')).toHaveClass('custom-content')
    })
  })

  describe('CardFooter', () => {
    it('renders footer section', () => {
      render(
        <Card>
          <CardFooter data-testid="footer">Footer content</CardFooter>
        </Card>
      )
      const footer = screen.getByTestId('footer')
      expect(footer).toBeInTheDocument()
      expect(footer).toHaveTextContent('Footer content')
    })

    it('applies footer styling', () => {
      render(<CardFooter data-testid="footer">Footer</CardFooter>)
      expect(screen.getByTestId('footer')).toHaveClass('flex', 'items-center')
    })

    it('applies custom className to CardFooter', () => {
      render(
        <CardFooter data-testid="footer" className="custom-footer">
          Footer
        </CardFooter>
      )
      expect(screen.getByTestId('footer')).toHaveClass('custom-footer')
    })
  })

  describe('Complete Card Composition', () => {
    it('renders all card components together', () => {
      render(
        <Card>
          <CardHeader>
            <CardTitle>Test Card</CardTitle>
            <CardDescription>Test description</CardDescription>
          </CardHeader>
          <CardContent>Card body content</CardContent>
          <CardFooter>Footer actions</CardFooter>
        </Card>
      )

      expect(screen.getByText('Test Card')).toBeInTheDocument()
      expect(screen.getByText('Test description')).toBeInTheDocument()
      expect(screen.getByText('Card body content')).toBeInTheDocument()
      expect(screen.getByText('Footer actions')).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('should not have accessibility violations for basic card', async () => {
      const { container } = render(
        <Card>
          <CardHeader>
            <CardTitle>Accessible Card</CardTitle>
            <CardDescription>This card should be accessible</CardDescription>
          </CardHeader>
          <CardContent>
            <p>Card content goes here</p>
          </CardContent>
          <CardFooter>
            <button>Action</button>
          </CardFooter>
        </Card>
      )
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })

    it('supports aria attributes', () => {
      render(
        <Card aria-label="Information card" role="article">
          <CardContent>Content</CardContent>
        </Card>
      )
      const card = screen.getByRole('article')
      expect(card).toHaveAttribute('aria-label', 'Information card')
    })
  })
})