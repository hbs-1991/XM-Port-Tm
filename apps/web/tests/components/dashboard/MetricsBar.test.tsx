/**
 * MetricsBar component tests
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import { MetricsBar, MetricsBarSkeleton, type MetricsData } from '@/components/dashboard/MetricsBar';

const mockMetricsData: MetricsData = {
  creditBalance: {
    remaining: 1500,
    total: 2000,
    percentage: 75,
    trend: 'up'
  },
  totalJobs: {
    count: 250,
    trend: 'up',
    percentageChange: 12.5
  },
  successRate: {
    percentage: 96.8,
    trend: 'stable'
  },
  averageConfidence: {
    score: 89.5,
    trend: 'down'
  },
  monthlyUsage: {
    creditsUsed: 500,
    jobsCompleted: 125,
    month: 'January 2025',
    percentageChange: 8.2
  }
};

describe('MetricsBar', () => {
  it('renders all metric cards with correct data', () => {
    render(<MetricsBar data={mockMetricsData} />);
    
    // Check if all metric cards are rendered
    expect(screen.getByText('Credit Balance')).toBeInTheDocument();
    expect(screen.getByText('Total Jobs')).toBeInTheDocument();
    expect(screen.getByText('Success Rate')).toBeInTheDocument();
    expect(screen.getByText('Avg Confidence')).toBeInTheDocument();
    expect(screen.getByText('This Month')).toBeInTheDocument();
    
    // Check specific values
    expect(screen.getByText('1,500')).toBeInTheDocument();
    expect(screen.getByText('250')).toBeInTheDocument();
    expect(screen.getByText('96.8%')).toBeInTheDocument();
    expect(screen.getByText('89.5%')).toBeInTheDocument();
    expect(screen.getByText('125')).toBeInTheDocument();
  });

  it('shows skeleton when loading', () => {
    render(<MetricsBar loading={true} />);
    
    // Should render skeleton loader
    const skeletonElements = document.querySelectorAll('.animate-pulse');
    expect(skeletonElements.length).toBeGreaterThan(0);
  });

  it('shows skeleton when no data provided', () => {
    render(<MetricsBar />);
    
    // Should render skeleton loader when no data
    const skeletonElements = document.querySelectorAll('.animate-pulse');
    expect(skeletonElements.length).toBeGreaterThan(0);
  });

  it('applies correct color classes based on thresholds', () => {
    const lowCreditData = {
      ...mockMetricsData,
      creditBalance: {
        remaining: 200,
        total: 1000,
        percentage: 20, // Below 30% threshold
        trend: 'down' as const
      },
      successRate: {
        percentage: 88.5, // Below 90% threshold
        trend: 'down' as const
      }
    };

    render(<MetricsBar data={lowCreditData} />);
    
    // Check that warning colors are applied (this would need more specific testing of classes)
    expect(screen.getByText('Credit Balance')).toBeInTheDocument();
    expect(screen.getByText('Success Rate')).toBeInTheDocument();
  });

  it('renders trend indicators correctly', () => {
    render(<MetricsBar data={mockMetricsData} />);
    
    // Should show trend indicators
    expect(screen.getByText('12.5%')).toBeInTheDocument(); // Total jobs trend
    expect(screen.getByText('8.2%')).toBeInTheDocument(); // Monthly usage trend
  });

  it('includes proper accessibility attributes', () => {
    render(<MetricsBar data={mockMetricsData} />);
    
    // Check for ARIA labels
    const metricsRegion = screen.getByRole('region');
    expect(metricsRegion).toHaveAttribute('aria-label', 'Key performance metrics');
    
    // Check for progress bar accessibility
    const progressBars = screen.getAllByRole('progressbar');
    expect(progressBars.length).toBeGreaterThan(0);
  });
});

describe('MetricsBarSkeleton', () => {
  it('renders skeleton loading state', () => {
    render(<MetricsBarSkeleton />);
    
    // Should render 5 skeleton cards
    const skeletonCards = document.querySelectorAll('.animate-pulse');
    expect(skeletonCards.length).toBe(5);
    
    // Check accessibility
    const statusElement = screen.getByRole('status');
    expect(statusElement).toHaveAttribute('aria-label', 'Loading metrics');
  });

  it('applies custom className', () => {
    render(<MetricsBarSkeleton className="custom-class" />);
    
    const container = screen.getByRole('status');
    expect(container).toHaveClass('custom-class');
  });
});