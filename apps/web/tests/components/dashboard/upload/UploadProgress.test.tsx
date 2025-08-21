import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { UploadProgress } from '@/components/dashboard/upload/UploadProgress';

describe('UploadProgress', () => {
  it('renders progress with correct percentage', () => {
    render(
      <UploadProgress 
        progress={45} 
        fileName="test.csv" 
      />
    );

    expect(screen.getByText('45%')).toBeInTheDocument();
    expect(screen.getByText('test.csv')).toBeInTheDocument();
  });

  it('shows appropriate status messages for different progress levels', () => {
    const { rerender } = render(
      <UploadProgress progress={10} fileName="test.csv" />
    );
    expect(screen.getByText('Validating file...')).toBeInTheDocument();

    rerender(<UploadProgress progress={30} fileName="test.csv" />);
    expect(screen.getByText('Uploading...')).toBeInTheDocument();

    rerender(<UploadProgress progress={60} fileName="test.csv" />);
    expect(screen.getByText('Processing data...')).toBeInTheDocument();

    rerender(<UploadProgress progress={85} fileName="test.csv" />);
    expect(screen.getByText('Finalizing...')).toBeInTheDocument();

    rerender(<UploadProgress progress={100} fileName="test.csv" />);
    expect(screen.getByText('Complete!')).toBeInTheDocument();
  });

  it('shows cancel button when showCancel is true', () => {
    const onCancel = jest.fn();

    render(
      <UploadProgress 
        progress={45} 
        fileName="test.csv" 
        onCancel={onCancel}
        showCancel={true}
      />
    );

    const cancelButton = screen.getByText('Cancel');
    expect(cancelButton).toBeInTheDocument();
  });

  it('hides cancel button when showCancel is false', () => {
    const onCancel = jest.fn();

    render(
      <UploadProgress 
        progress={45} 
        fileName="test.csv" 
        onCancel={onCancel}
        showCancel={false}
      />
    );

    expect(screen.queryByText('Cancel')).not.toBeInTheDocument();
  });

  it('calls onCancel when cancel button is clicked', async () => {
    const user = userEvent.setup();
    const onCancel = jest.fn();

    render(
      <UploadProgress 
        progress={45} 
        fileName="test.csv" 
        onCancel={onCancel}
        showCancel={true}
      />
    );

    const cancelButton = screen.getByText('Cancel');
    await user.click(cancelButton);

    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('shows loading spinner', () => {
    render(
      <UploadProgress 
        progress={45} 
        fileName="test.csv" 
      />
    );

    // The Loader2 icon should be present with animate-spin class
    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toBeInTheDocument();
  });

  it('displays file name correctly', () => {
    render(
      <UploadProgress 
        progress={45} 
        fileName="very-long-filename-with-extension.xlsx" 
      />
    );

    expect(screen.getByText('very-long-filename-with-extension.xlsx')).toBeInTheDocument();
  });

  it('handles zero progress', () => {
    render(
      <UploadProgress 
        progress={0} 
        fileName="test.csv" 
      />
    );

    expect(screen.getByText('0%')).toBeInTheDocument();
    expect(screen.getByText('Validating file...')).toBeInTheDocument();
  });

  it('handles 100% progress', () => {
    render(
      <UploadProgress 
        progress={100} 
        fileName="test.csv" 
      />
    );

    expect(screen.getByText('100%')).toBeInTheDocument();
    expect(screen.getByText('Complete!')).toBeInTheDocument();
  });

  it('handles progress values above 100', () => {
    render(
      <UploadProgress 
        progress={150} 
        fileName="test.csv" 
      />
    );

    // Should handle gracefully - exact behavior depends on Progress component
    expect(screen.getByText('Complete!')).toBeInTheDocument();
  });

  it('works without onCancel handler', () => {
    render(
      <UploadProgress 
        progress={45} 
        fileName="test.csv" 
        showCancel={false}
      />
    );

    // Should render without error
    expect(screen.getByText('45%')).toBeInTheDocument();
  });

  it('displays correct progress bar value', () => {
    render(
      <UploadProgress 
        progress={75} 
        fileName="test.csv" 
      />
    );

    // The Progress component should receive the correct value
    // This would need to be tested with the actual Progress component
    expect(screen.getByText('75%')).toBeInTheDocument();
  });
});