/**
 * Test cases for download functionality in JobHistory component
 */

import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import JobHistory from '@/components/dashboard/JobHistory'

// Mock fetch globally
global.fetch = jest.fn()

describe('Download Functionality', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    // Reset fetch mock
    ;(global.fetch as jest.Mock).mockClear()
  })

  const mockJobsWithDownload = {
    jobs: [
      {
        id: 'job-1',
        input_file_name: 'test_products.xlsx',
        status: 'COMPLETED',
        has_xml_output: true,
        xml_generation_status: 'COMPLETED',
        created_at: '2025-01-15T10:30:00Z',
        completed_at: '2025-01-15T10:32:00Z',
        processing_time_ms: 120000,
        total_products: 100,
        successful_matches: 95,
        credits_used: 10
      }
    ],
    total: 1,
    page: 1,
    limit: 50,
    totalPages: 1
  }

  const mockJobsWithoutDownload = {
    jobs: [
      {
        id: 'job-2',
        input_file_name: 'processing.xlsx',
        status: 'PROCESSING',
        has_xml_output: false,
        xml_generation_status: 'PENDING',
        created_at: '2025-01-15T11:00:00Z',
        completed_at: null,
        processing_time_ms: null,
        total_products: 0,
        successful_matches: 0,
        credits_used: 0
      }
    ],
    total: 1,
    page: 1,
    limit: 50,
    totalPages: 1
  }

  it('shows download button for completed jobs with XML output', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockJobsWithDownload
    })

    render(<JobHistory />)

    await waitFor(() => {
      expect(screen.getByText('test_products.xlsx')).toBeInTheDocument()
    })

    // Should show download button for completed job with XML
    const downloadButton = screen.getByRole('button', { name: /download/i })
    expect(downloadButton).toBeInTheDocument()
  })

  it('hides download button for jobs without XML output', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockJobsWithoutDownload
    })

    render(<JobHistory />)

    await waitFor(() => {
      expect(screen.getByText('processing.xlsx')).toBeInTheDocument()
    })

    // Should not show download button for job without XML output
    expect(screen.queryByRole('button', { name: /download/i })).not.toBeInTheDocument()
  })

  it('handles successful download', async () => {
    // Mock the jobs fetch
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockJobsWithDownload
    })

    render(<JobHistory />)

    await waitFor(() => {
      expect(screen.getByText('test_products.xlsx')).toBeInTheDocument()
    })

    // Mock successful download info fetch
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        job_id: 'job-1',
        download_url: 'https://test-bucket.s3.amazonaws.com/test-file.xml',
        file_name: 'asycuda_export_job-1.xml'
      })
    })

    // Mock successful file download
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      blob: async () => new Blob(['<xml>test</xml>'], { type: 'application/xml' })
    })

    // Mock DOM methods
    const mockCreateElement = jest.spyOn(document, 'createElement')
    const mockAppendChild = jest.spyOn(document.body, 'appendChild')
    const mockRemoveChild = jest.spyOn(document.body, 'removeChild')
    const mockClick = jest.fn()
    const mockCreateObjectURL = jest.spyOn(window.URL, 'createObjectURL')
    const mockRevokeObjectURL = jest.spyOn(window.URL, 'revokeObjectURL')

    mockCreateElement.mockReturnValue({
      ...document.createElement('a'),
      click: mockClick
    } as any)
    mockCreateObjectURL.mockReturnValue('blob:test-url')

    const downloadButton = screen.getByRole('button', { name: /download/i })
    fireEvent.click(downloadButton)

    await waitFor(() => {
      expect(mockClick).toHaveBeenCalled()
      expect(mockCreateObjectURL).toHaveBeenCalled()
      expect(mockRevokeObjectURL).toHaveBeenCalled()
    })

    // Cleanup
    mockCreateElement.mockRestore()
    mockAppendChild.mockRestore()
    mockRemoveChild.mockRestore()
    mockCreateObjectURL.mockRestore()
    mockRevokeObjectURL.mockRestore()
  })

  it('handles XML not available error', async () => {
    // Mock the jobs fetch
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockJobsWithDownload
    })

    render(<JobHistory />)

    await waitFor(() => {
      expect(screen.getByText('test_products.xlsx')).toBeInTheDocument()
    })

    // Mock XML not available error
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      json: async () => ({
        detail: {
          error: 'xml_not_available',
          message: 'XML file has not been generated for this job'
        }
      })
    })

    // Mock alert
    const mockAlert = jest.spyOn(window, 'alert').mockImplementation(() => {})

    const downloadButton = screen.getByRole('button', { name: /download/i })
    fireEvent.click(downloadButton)

    await waitFor(() => {
      expect(mockAlert).toHaveBeenCalledWith(
        'XML file is not available for download. The processing may still be in progress.'
      )
    })

    mockAlert.mockRestore()
  })

  it('handles expired download link error', async () => {
    // Mock the jobs fetch
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockJobsWithDownload
    })

    render(<JobHistory />)

    await waitFor(() => {
      expect(screen.getByText('test_products.xlsx')).toBeInTheDocument()
    })

    // Mock expired link error
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      json: async () => ({
        detail: {
          error: 'download_url_generation_failed',
          message: 'Failed to generate download URL'
        }
      })
    })

    // Mock alert
    const mockAlert = jest.spyOn(window, 'alert').mockImplementation(() => {})

    const downloadButton = screen.getByRole('button', { name: /download/i })
    fireEvent.click(downloadButton)

    await waitFor(() => {
      expect(mockAlert).toHaveBeenCalledWith(
        'The download link has expired. Please try again.'
      )
    })

    mockAlert.mockRestore()
  })

  it('handles job not found error', async () => {
    // Mock the jobs fetch
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockJobsWithDownload
    })

    render(<JobHistory />)

    await waitFor(() => {
      expect(screen.getByText('test_products.xlsx')).toBeInTheDocument()
    })

    // Mock job not found error
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      json: async () => ({
        detail: {
          error: 'job_not_found',
          message: 'Processing job not found or access denied'
        }
      })
    })

    // Mock alert
    const mockAlert = jest.spyOn(window, 'alert').mockImplementation(() => {})

    const downloadButton = screen.getByRole('button', { name: /download/i })
    fireEvent.click(downloadButton)

    await waitFor(() => {
      expect(mockAlert).toHaveBeenCalledWith(
        'Processing job not found or you do not have access to this file.'
      )
    })

    mockAlert.mockRestore()
  })

  it('handles file download failure from storage', async () => {
    // Mock the jobs fetch
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockJobsWithDownload
    })

    render(<JobHistory />)

    await waitFor(() => {
      expect(screen.getByText('test_products.xlsx')).toBeInTheDocument()
    })

    // Mock successful download info fetch
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        job_id: 'job-1',
        download_url: 'https://test-bucket.s3.amazonaws.com/test-file.xml',
        file_name: 'asycuda_export_job-1.xml'
      })
    })

    // Mock failed file download
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 404
    })

    // Mock alert
    const mockAlert = jest.spyOn(window, 'alert').mockImplementation(() => {})

    const downloadButton = screen.getByRole('button', { name: /download/i })
    fireEvent.click(downloadButton)

    await waitFor(() => {
      expect(mockAlert).toHaveBeenCalledWith(
        'Failed to download file from storage. The file may have been moved or deleted.'
      )
    })

    mockAlert.mockRestore()
  })
})