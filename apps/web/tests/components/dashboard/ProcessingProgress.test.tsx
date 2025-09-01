import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import ProcessingProgress from '@/components/dashboard/ProcessingProgress'

describe('ProcessingProgress', () => {
  const defaultProps = {
    jobId: 'test-job-123456789',
    fileName: 'test-file.csv',
    status: 'PROCESSING',
    progress: 50,
    message: 'Processing products...'
  }

  it('should render job information correctly', () => {
    render(<ProcessingProgress {...defaultProps} />)

    expect(screen.getByText('test-file.csv')).toBeInTheDocument()
    expect(screen.getByText('PROCESSING')).toBeInTheDocument()
    expect(screen.getByText('Job ID: test-job')).toBeInTheDocument() // Should be truncated
  })

  it('should show spinner and progress bar for active statuses', () => {
    render(<ProcessingProgress {...defaultProps} status="PROCESSING" />)

    // Should show spinning loader
    expect(document.querySelector('.animate-spin')).toBeInTheDocument()
    
    // Should show progress bar
    expect(screen.getByLabelText('Processing progress: 50%')).toBeInTheDocument()
    
    // Should show progress message
    expect(screen.getByText('Processing products...')).toBeInTheDocument()
    expect(screen.getByText('50%')).toBeInTheDocument()
  })

  it('should show spinner and progress bar for pending status', () => {
    render(<ProcessingProgress {...defaultProps} status="PENDING" progress={0} />)

    expect(document.querySelector('.animate-spin')).toBeInTheDocument()
    expect(screen.getByLabelText('Processing progress: 0%')).toBeInTheDocument()
  })

  it('should not show spinner or progress bar for completed status', () => {
    render(
      <ProcessingProgress 
        {...defaultProps} 
        status="COMPLETED" 
        progress={100} 
        message="Processing completed successfully"
      />
    )

    expect(document.querySelector('.animate-spin')).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/Processing progress/)).not.toBeInTheDocument()
    expect(screen.getByText('Processing completed successfully')).toBeInTheDocument()
  })

  it('should not show spinner or progress bar for failed status', () => {
    render(
      <ProcessingProgress 
        {...defaultProps} 
        status="FAILED" 
        progress={0} 
        message="Processing failed due to invalid format"
      />
    )

    expect(document.querySelector('.animate-spin')).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/Processing progress/)).not.toBeInTheDocument()
    expect(screen.getByText('Processing failed due to invalid format')).toBeInTheDocument()
  })

  it('should apply correct styling for active jobs', () => {
    const { container } = render(<ProcessingProgress {...defaultProps} status="PROCESSING" />)

    expect(container.querySelector('.border-l-blue-500')).toBeInTheDocument()
  })

  it('should apply correct styling for inactive jobs', () => {
    const { container } = render(<ProcessingProgress {...defaultProps} status="COMPLETED" />)

    expect(container.querySelector('.border-l-gray-300')).toBeInTheDocument()
  })

  it('should display correct status colors', () => {
    const { rerender } = render(<ProcessingProgress {...defaultProps} status="PENDING" />)
    expect(screen.getByText('PENDING')).toHaveClass('bg-yellow-100', 'text-yellow-800')

    rerender(<ProcessingProgress {...defaultProps} status="PROCESSING" />)
    expect(screen.getByText('PROCESSING')).toHaveClass('bg-blue-100', 'text-blue-800')

    rerender(<ProcessingProgress {...defaultProps} status="COMPLETED" />)
    expect(screen.getByText('COMPLETED')).toHaveClass('bg-green-100', 'text-green-800')

    rerender(<ProcessingProgress {...defaultProps} status="FAILED" />)
    expect(screen.getByText('FAILED')).toHaveClass('bg-red-100', 'text-red-800')
  })

  it('should handle unknown status gracefully', () => {
    render(<ProcessingProgress {...defaultProps} status="UNKNOWN_STATUS" />)

    expect(screen.getByText('UNKNOWN_STATUS')).toHaveClass('bg-gray-100', 'text-gray-800')
  })

  it('should truncate long file names with title attribute', () => {
    const longFileName = 'very-long-file-name-that-should-be-truncated-in-the-ui.csv'
    render(<ProcessingProgress {...defaultProps} fileName={longFileName} />)

    const fileNameElement = screen.getByText(longFileName)
    expect(fileNameElement).toHaveAttribute('title', longFileName)
    expect(fileNameElement).toHaveClass('truncate', 'max-w-[200px]')
  })

  it('should truncate job ID to 8 characters', () => {
    const longJobId = 'very-long-job-id-123456789abcdef'
    render(<ProcessingProgress {...defaultProps} jobId={longJobId} />)

    expect(screen.getByText('Job ID: very-lon')).toBeInTheDocument()
  })

  it('should render without message when not provided', () => {
    const { message, ...propsWithoutMessage } = defaultProps
    render(<ProcessingProgress {...propsWithoutMessage} status="PROCESSING" />)

    expect(screen.getByText('Processing...')).toBeInTheDocument()
  })

  it('should apply custom className', () => {
    const { container } = render(
      <ProcessingProgress {...defaultProps} className="custom-class" />
    )

    expect(container.firstChild).toHaveClass('custom-class')
  })

  it('should render progress bar with correct value', () => {
    render(<ProcessingProgress {...defaultProps} progress={75} />)

    const progressBar = screen.getByLabelText('Processing progress: 75%')
    expect(progressBar).toBeInTheDocument()
    expect(screen.getByText('75%')).toBeInTheDocument()
  })

  it('should handle edge case progress values', () => {
    const { rerender } = render(<ProcessingProgress {...defaultProps} progress={0} />)
    expect(screen.getByText('0%')).toBeInTheDocument()

    rerender(<ProcessingProgress {...defaultProps} progress={100} />)
    expect(screen.getByText('100%')).toBeInTheDocument()

    rerender(<ProcessingProgress {...defaultProps} progress={33.7} />)
    expect(screen.getByText('34%')).toBeInTheDocument() // Should be rounded
  })

  it('should have proper accessibility attributes', () => {
    render(<ProcessingProgress {...defaultProps} />)

    const progressBar = screen.getByLabelText('Processing progress: 50%')
    expect(progressBar).toBeInTheDocument()
    
    // File name should be accessible
    const fileName = screen.getByText('test-file.csv')
    expect(fileName).toBeInTheDocument()
  })

  it('should case-insensitive status checking', () => {
    render(<ProcessingProgress {...defaultProps} status="processing" />)

    expect(document.querySelector('.animate-spin')).toBeInTheDocument()
    expect(screen.getByLabelText(/Processing progress/)).toBeInTheDocument()
  })

  it('should handle empty or null message gracefully', () => {
    render(<ProcessingProgress {...defaultProps} message="" status="COMPLETED" />)
    
    // Should not show empty message, but still render component
    expect(screen.getByText('COMPLETED')).toBeInTheDocument()
  })
})