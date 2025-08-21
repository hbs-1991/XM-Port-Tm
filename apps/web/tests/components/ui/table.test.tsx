import React from 'react'
import { render, screen } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'jest-axe'
import {
  Table,
  TableHeader,
  TableBody,
  TableFooter,
  TableHead,
  TableRow,
  TableCell,
  TableCaption,
} from '@/components/shared/ui/table'

expect.extend(toHaveNoViolations)

describe('Table Component', () => {
  it('renders table element', () => {
    render(
      <Table>
        <TableBody>
          <TableRow>
            <TableCell>Cell content</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    )
    
    expect(screen.getByRole('table')).toBeInTheDocument()
    expect(screen.getByText('Cell content')).toBeInTheDocument()
  })

  it('applies custom className to Table', () => {
    render(
      <Table className="custom-table">
        <TableBody>
          <TableRow>
            <TableCell>Content</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    )
    
    const table = screen.getByRole('table')
    expect(table).toHaveClass('custom-table')
  })

  it('wraps table in scrollable container', () => {
    const { container } = render(
      <Table>
        <TableBody>
          <TableRow>
            <TableCell>Content</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    )
    
    const wrapper = container.querySelector('.overflow-auto')
    expect(wrapper).toBeInTheDocument()
  })

  it('forwards ref to table element', () => {
    const ref = React.createRef<HTMLTableElement>()
    render(
      <Table ref={ref}>
        <TableBody>
          <TableRow>
            <TableCell>Content</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    )
    
    expect(ref.current).toBeInstanceOf(HTMLTableElement)
  })

  describe('TableHeader', () => {
    it('renders thead element', () => {
      render(
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Header</TableHead>
            </TableRow>
          </TableHeader>
        </Table>
      )
      
      const thead = document.querySelector('thead')
      expect(thead).toBeInTheDocument()
      expect(screen.getByText('Header')).toBeInTheDocument()
    })

    it('applies custom className to TableHeader', () => {
      render(
        <Table>
          <TableHeader className="custom-header">
            <TableRow>
              <TableHead>Header</TableHead>
            </TableRow>
          </TableHeader>
        </Table>
      )
      
      const thead = document.querySelector('thead')
      expect(thead).toHaveClass('custom-header')
    })
  })

  describe('TableBody', () => {
    it('renders tbody element', () => {
      render(
        <Table>
          <TableBody>
            <TableRow>
              <TableCell>Body content</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      )
      
      const tbody = document.querySelector('tbody')
      expect(tbody).toBeInTheDocument()
      expect(screen.getByText('Body content')).toBeInTheDocument()
    })

    it('applies custom className to TableBody', () => {
      render(
        <Table>
          <TableBody className="custom-body">
            <TableRow>
              <TableCell>Content</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      )
      
      const tbody = document.querySelector('tbody')
      expect(tbody).toHaveClass('custom-body')
    })
  })

  describe('TableFooter', () => {
    it('renders tfoot element', () => {
      render(
        <Table>
          <TableFooter>
            <TableRow>
              <TableCell>Footer content</TableCell>
            </TableRow>
          </TableFooter>
        </Table>
      )
      
      const tfoot = document.querySelector('tfoot')
      expect(tfoot).toBeInTheDocument()
      expect(screen.getByText('Footer content')).toBeInTheDocument()
    })

    it('applies footer styling', () => {
      render(
        <Table>
          <TableFooter>
            <TableRow>
              <TableCell>Footer</TableCell>
            </TableRow>
          </TableFooter>
        </Table>
      )
      
      const tfoot = document.querySelector('tfoot')
      expect(tfoot).toHaveClass('border-t', 'bg-muted/50')
    })

    it('applies custom className to TableFooter', () => {
      render(
        <Table>
          <TableFooter className="custom-footer">
            <TableRow>
              <TableCell>Footer</TableCell>
            </TableRow>
          </TableFooter>
        </Table>
      )
      
      const tfoot = document.querySelector('tfoot')
      expect(tfoot).toHaveClass('custom-footer')
    })
  })

  describe('TableRow', () => {
    it('renders tr element', () => {
      render(
        <Table>
          <TableBody>
            <TableRow data-testid="row">
              <TableCell>Row content</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      )
      
      expect(screen.getByTestId('row')).toBeInTheDocument()
      expect(screen.getByText('Row content')).toBeInTheDocument()
    })

    it('applies hover styling', () => {
      render(
        <Table>
          <TableBody>
            <TableRow data-testid="row">
              <TableCell>Content</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      )
      
      expect(screen.getByTestId('row')).toHaveClass('hover:bg-muted/50')
    })

    it('supports selected state', () => {
      render(
        <Table>
          <TableBody>
            <TableRow data-state="selected" data-testid="row">
              <TableCell>Selected row</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      )
      
      expect(screen.getByTestId('row')).toHaveClass('data-[state=selected]:bg-muted')
    })

    it('applies custom className to TableRow', () => {
      render(
        <Table>
          <TableBody>
            <TableRow className="custom-row" data-testid="row">
              <TableCell>Content</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      )
      
      expect(screen.getByTestId('row')).toHaveClass('custom-row')
    })
  })

  describe('TableHead', () => {
    it('renders th element', () => {
      render(
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Column Header</TableHead>
            </TableRow>
          </TableHeader>
        </Table>
      )
      
      const th = screen.getByRole('columnheader')
      expect(th).toBeInTheDocument()
      expect(th).toHaveTextContent('Column Header')
    })

    it('applies header cell styling', () => {
      render(
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Header</TableHead>
            </TableRow>
          </TableHeader>
        </Table>
      )
      
      const th = screen.getByRole('columnheader')
      expect(th).toHaveClass('font-medium', 'text-muted-foreground')
    })

    it('supports scope attribute', () => {
      render(
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead scope="col">Column</TableHead>
            </TableRow>
          </TableHeader>
        </Table>
      )
      
      const th = screen.getByRole('columnheader')
      expect(th).toHaveAttribute('scope', 'col')
    })

    it('applies custom className to TableHead', () => {
      render(
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="custom-head">Header</TableHead>
            </TableRow>
          </TableHeader>
        </Table>
      )
      
      expect(screen.getByRole('columnheader')).toHaveClass('custom-head')
    })
  })

  describe('TableCell', () => {
    it('renders td element', () => {
      render(
        <Table>
          <TableBody>
            <TableRow>
              <TableCell>Cell Data</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      )
      
      const td = screen.getByRole('cell')
      expect(td).toBeInTheDocument()
      expect(td).toHaveTextContent('Cell Data')
    })

    it('applies cell styling', () => {
      render(
        <Table>
          <TableBody>
            <TableRow>
              <TableCell>Content</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      )
      
      const td = screen.getByRole('cell')
      expect(td).toHaveClass('p-4', 'align-middle')
    })

    it('supports colspan attribute', () => {
      render(
        <Table>
          <TableBody>
            <TableRow>
              <TableCell colSpan={2}>Spanning cell</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      )
      
      const td = screen.getByRole('cell')
      expect(td).toHaveAttribute('colspan', '2')
    })

    it('applies custom className to TableCell', () => {
      render(
        <Table>
          <TableBody>
            <TableRow>
              <TableCell className="custom-cell">Content</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      )
      
      expect(screen.getByRole('cell')).toHaveClass('custom-cell')
    })
  })

  describe('TableCaption', () => {
    it('renders caption element', () => {
      render(
        <Table>
          <TableCaption>Table caption text</TableCaption>
          <TableBody>
            <TableRow>
              <TableCell>Content</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      )
      
      const caption = screen.getByText('Table caption text')
      expect(caption).toBeInTheDocument()
      expect(caption.tagName).toBe('CAPTION')
    })

    it('applies caption styling', () => {
      render(
        <Table>
          <TableCaption>Caption</TableCaption>
          <TableBody>
            <TableRow>
              <TableCell>Content</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      )
      
      const caption = screen.getByText('Caption')
      expect(caption).toHaveClass('text-sm', 'text-muted-foreground')
    })

    it('applies custom className to TableCaption', () => {
      render(
        <Table>
          <TableCaption className="custom-caption">Caption</TableCaption>
          <TableBody>
            <TableRow>
              <TableCell>Content</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      )
      
      const caption = screen.getByText('Caption')
      expect(caption).toHaveClass('custom-caption')
    })
  })

  describe('Complete Table Structure', () => {
    it('renders a complete table with all sections', () => {
      render(
        <Table>
          <TableCaption>User data table</TableCaption>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Role</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell>John Doe</TableCell>
              <TableCell>john@example.com</TableCell>
              <TableCell>Admin</TableCell>
            </TableRow>
            <TableRow>
              <TableCell>Jane Smith</TableCell>
              <TableCell>jane@example.com</TableCell>
              <TableCell>User</TableCell>
            </TableRow>
          </TableBody>
          <TableFooter>
            <TableRow>
              <TableCell colSpan={3}>Total: 2 users</TableCell>
            </TableRow>
          </TableFooter>
        </Table>
      )
      
      expect(screen.getByText('User data table')).toBeInTheDocument()
      expect(screen.getByText('Name')).toBeInTheDocument()
      expect(screen.getByText('John Doe')).toBeInTheDocument()
      expect(screen.getByText('jane@example.com')).toBeInTheDocument()
      expect(screen.getByText('Total: 2 users')).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('should not have accessibility violations', async () => {
      const { container } = render(
        <Table>
          <TableCaption>Accessible table</TableCaption>
          <TableHeader>
            <TableRow>
              <TableHead scope="col">Column 1</TableHead>
              <TableHead scope="col">Column 2</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell>Data 1</TableCell>
              <TableCell>Data 2</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      )
      
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })

    it('supports row headers for accessibility', () => {
      render(
        <Table>
          <TableBody>
            <TableRow>
              <TableHead scope="row">Row Header</TableHead>
              <TableCell>Data</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      )
      
      const rowHeader = screen.getByRole('rowheader')
      expect(rowHeader).toBeInTheDocument()
      expect(rowHeader).toHaveAttribute('scope', 'row')
    })

    it('provides semantic table structure', () => {
      render(
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Header</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell>Cell</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      )
      
      expect(screen.getByRole('table')).toBeInTheDocument()
      expect(screen.getByRole('columnheader')).toBeInTheDocument()
      expect(screen.getByRole('cell')).toBeInTheDocument()
    })
  })
})