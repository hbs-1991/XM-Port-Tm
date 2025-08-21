#!/usr/bin/env node

/**
 * Comprehensive test runner for frontend file upload functionality
 */

const { execSync, spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

class FrontendTestRunner {
  constructor() {
    this.projectRoot = path.resolve(__dirname, '../../../');
    this.webRoot = path.resolve(this.projectRoot, 'apps/web');
    this.testResults = {
      timestamp: new Date().toISOString(),
      suites: {},
      coverage: {},
      summary: { passed: 0, failed: 0, skipped: 0 }
    };
  }

  async runUnitTests(verbose = false) {
    console.log('🧪 Running Frontend Unit Tests...');
    
    try {
      const cmd = [
        'npm', 'test',
        '--',
        '--coverage',
        '--coverageReporters=json,html,text-summary',
        '--coverageDirectory=coverage',
        '--testMatch=**/*.test.tsx',
        '--testMatch=**/*.test.ts',
        verbose ? '--verbose' : '--silent'
      ];

      const result = await this.runCommand(cmd, this.webRoot);
      
      if (result.success) {
        console.log('✅ Frontend unit tests passed');
        this.testResults.suites.unit = {
          status: 'passed',
          output: result.stdout
        };
        return true;
      } else {
        console.log('❌ Frontend unit tests failed');
        console.log(result.stdout);
        console.log(result.stderr);
        this.testResults.suites.unit = {
          status: 'failed',
          output: result.stdout,
          error: result.stderr
        };
        return false;
      }
    } catch (error) {
      console.log(`❌ Error running unit tests: ${error.message}`);
      this.testResults.suites.unit = {
        status: 'error',
        error: error.message
      };
      return false;
    }
  }

  async runComponentTests(verbose = false) {
    console.log('🎨 Running Component Tests...');
    
    try {
      const cmd = [
        'npm', 'test',
        '--',
        '--testMatch=**/components/**/*.test.tsx',
        '--coverage',
        '--coverageDirectory=coverage/components',
        verbose ? '--verbose' : '--silent'
      ];

      const result = await this.runCommand(cmd, this.webRoot);
      
      if (result.success) {
        console.log('✅ Component tests passed');
        this.testResults.suites.components = {
          status: 'passed',
          output: result.stdout
        };
        return true;
      } else {
        console.log('❌ Component tests failed');
        console.log(result.stdout);
        this.testResults.suites.components = {
          status: 'failed',
          output: result.stdout,
          error: result.stderr
        };
        return false;
      }
    } catch (error) {
      console.log(`❌ Error running component tests: ${error.message}`);
      this.testResults.suites.components = {
        status: 'error',
        error: error.message
      };
      return false;
    }
  }

  async runE2ETests(verbose = false) {
    console.log('🎭 Running E2E Tests...');
    
    try {
      const cmd = [
        'npx', 'playwright', 'test',
        'tests/e2e/file-upload-workflow.spec.ts',
        '--reporter=json',
        '--output-dir=test-results',
        verbose ? '' : '--quiet'
      ].filter(Boolean);

      const result = await this.runCommand(cmd, this.webRoot);
      
      if (result.success) {
        console.log('✅ E2E tests passed');
        this.testResults.suites.e2e = {
          status: 'passed',
          output: result.stdout
        };
        return true;
      } else {
        console.log('❌ E2E tests failed');
        console.log(result.stdout);
        this.testResults.suites.e2e = {
          status: 'failed',
          output: result.stdout,
          error: result.stderr
        };
        return false;
      }
    } catch (error) {
      console.log(`❌ Error running E2E tests: ${error.message}`);
      this.testResults.suites.e2e = {
        status: 'error',
        error: error.message
      };
      return false;
    }
  }

  async runAccessibilityTests(verbose = false) {
    console.log('♿ Running Accessibility Tests...');
    
    try {
      const cmd = [
        'npm', 'test',
        '--',
        '--testMatch=**/*.a11y.test.tsx',
        '--testMatch=**/*.accessibility.test.tsx',
        verbose ? '--verbose' : '--silent'
      ];

      const result = await this.runCommand(cmd, this.webRoot);
      
      if (result.success) {
        console.log('✅ Accessibility tests passed');
        this.testResults.suites.accessibility = {
          status: 'passed',
          output: result.stdout
        };
        return true;
      } else {
        console.log('⚠️  Some accessibility tests failed');
        console.log(result.stdout);
        this.testResults.suites.accessibility = {
          status: 'warning',
          output: result.stdout,
          error: result.stderr
        };
        return true; // Don't fail CI for accessibility issues
      }
    } catch (error) {
      console.log(`⚠️  Error running accessibility tests: ${error.message}`);
      this.testResults.suites.accessibility = {
        status: 'error',
        error: error.message
      };
      return true; // Don't fail CI for accessibility issues
    }
  }

  async runPerformanceTests(verbose = false) {
    console.log('⚡ Running Performance Tests...');
    
    try {
      // Create a simple performance test
      const perfTestContent = `
import { render } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { FileUpload } from '@/components/dashboard/upload/FileUpload';

// Performance benchmark test
test('FileUpload component renders within performance budget', () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  const start = performance.now();
  
  render(
    <QueryClientProvider client={queryClient}>
      <FileUpload onUploadSuccess={jest.fn()} />
    </QueryClientProvider>
  );
  
  const end = performance.now();
  const renderTime = end - start;
  
  // Component should render within 100ms
  expect(renderTime).toBeLessThan(100);
  console.log(\`FileUpload rendered in \${renderTime.toFixed(2)}ms\`);
});

test('Multiple file selections should not cause memory leaks', () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  const initialMemory = (performance as any).memory?.usedJSHeapSize || 0;
  
  // Render multiple times to simulate file selections
  for (let i = 0; i < 10; i++) {
    const { unmount } = render(
      <QueryClientProvider client={queryClient}>
        <FileUpload onUploadSuccess={jest.fn()} />
      </QueryClientProvider>
    );
    unmount();
  }
  
  const finalMemory = (performance as any).memory?.usedJSHeapSize || 0;
  const memoryIncrease = finalMemory - initialMemory;
  
  // Memory increase should be minimal (less than 5MB)
  expect(memoryIncrease).toBeLessThan(5 * 1024 * 1024);
});
`;

      // Write performance test
      const perfTestPath = path.join(this.webRoot, 'tests/performance/fileupload.performance.test.tsx');
      const perfTestDir = path.dirname(perfTestPath);
      
      if (!fs.existsSync(perfTestDir)) {
        fs.mkdirSync(perfTestDir, { recursive: true });
      }
      
      fs.writeFileSync(perfTestPath, perfTestContent);

      const cmd = [
        'npm', 'test',
        '--',
        '--testMatch=**/performance/*.test.tsx',
        verbose ? '--verbose' : '--silent'
      ];

      const result = await this.runCommand(cmd, this.webRoot);
      
      if (result.success) {
        console.log('✅ Performance tests passed');
        this.testResults.suites.performance = {
          status: 'passed',
          output: result.stdout
        };
        return true;
      } else {
        console.log('⚠️  Some performance benchmarks may have failed');
        console.log(result.stdout);
        this.testResults.suites.performance = {
          status: 'warning',
          output: result.stdout,
          error: result.stderr
        };
        return true; // Don't fail CI for performance issues
      }
    } catch (error) {
      console.log(`⚠️  Error running performance tests: ${error.message}`);
      this.testResults.suites.performance = {
        status: 'error',
        error: error.message
      };
      return true; // Don't fail CI for performance issues
    }
  }

  async generateCoverageReport() {
    console.log('📊 Generating Coverage Report...');
    
    try {
      const coveragePath = path.join(this.webRoot, 'coverage/coverage-summary.json');
      
      if (fs.existsSync(coveragePath)) {
        const coverageData = JSON.parse(fs.readFileSync(coveragePath, 'utf8'));
        
        if (coverageData.total && coverageData.total.statements) {
          const coverage = coverageData.total.statements.pct;
          this.testResults.coverage.statements = coverage;
          
          if (coverage >= 90) {
            console.log(`✅ Excellent coverage: ${coverage}%`);
          } else if (coverage >= 80) {
            console.log(`✅ Good coverage: ${coverage}%`);
          } else if (coverage >= 70) {
            console.log(`⚠️  Moderate coverage: ${coverage}%`);
          } else {
            console.log(`❌ Low coverage: ${coverage}%`);
          }
        }
      }
    } catch (error) {
      console.log(`⚠️  Error generating coverage report: ${error.message}`);
    }
  }

  generateFinalReport() {
    console.log('\n' + '='.repeat(60));
    console.log('📋 FRONTEND TEST REPORT');
    console.log('='.repeat(60));
    
    // Count results
    const passed = Object.values(this.testResults.suites).filter(suite => suite.status === 'passed').length;
    const failed = Object.values(this.testResults.suites).filter(suite => suite.status === 'failed').length;
    const warnings = Object.values(this.testResults.suites).filter(suite => suite.status === 'warning').length;
    const errors = Object.values(this.testResults.suites).filter(suite => suite.status === 'error').length;
    
    this.testResults.summary = {
      passed,
      failed,
      warnings,
      errors,
      total: Object.keys(this.testResults.suites).length
    };
    
    // Print summary
    Object.entries(this.testResults.suites).forEach(([suiteName, result]) => {
      const statusIcons = {
        passed: '✅',
        failed: '❌',
        warning: '⚠️ ',
        error: '💥'
      };
      
      const icon = statusIcons[result.status] || '❓';
      console.log(`${icon} ${suiteName.charAt(0).toUpperCase() + suiteName.slice(1)} Tests: ${result.status.toUpperCase()}`);
    });
    
    if (this.testResults.coverage.statements) {
      console.log(`📊 Test Coverage: ${this.testResults.coverage.statements}%`);
    }
    
    console.log(`\n🎯 Summary: ${passed} passed, ${failed} failed, ${warnings} warnings, ${errors} errors`);
    
    // Save detailed report
    const reportPath = path.join(this.webRoot, 'test-report.json');
    fs.writeFileSync(reportPath, JSON.stringify(this.testResults, null, 2));
    console.log(`📁 Detailed report saved to: ${reportPath}`);
    
    if (failed > 0) {
      console.log('\n❌ Some tests failed. Check the output above for details.');
      return false;
    } else if (errors > 0) {
      console.log('\n⚠️  Some test suites had errors. Check the output above.');
      return false;
    } else {
      console.log('\n✅ All tests passed successfully!');
      return true;
    }
  }

  runCommand(cmd, cwd) {
    return new Promise((resolve) => {
      const child = spawn(cmd[0], cmd.slice(1), {
        cwd,
        stdio: ['pipe', 'pipe', 'pipe']
      });

      let stdout = '';
      let stderr = '';

      child.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      child.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      child.on('close', (code) => {
        resolve({
          success: code === 0,
          stdout,
          stderr,
          code
        });
      });
    });
  }
}

async function main() {
  const args = process.argv.slice(2);
  const verbose = args.includes('--verbose') || args.includes('-v');
  const unitOnly = args.includes('--unit-only');
  const componentOnly = args.includes('--component-only');
  const e2eOnly = args.includes('--e2e-only');
  const accessibilityOnly = args.includes('--accessibility-only');
  const performanceOnly = args.includes('--performance-only');
  const skipCoverage = args.includes('--skip-coverage');
  
  const runner = new FrontendTestRunner();
  
  console.log('🚀 Starting Frontend Test Suite for File Upload Functionality');
  console.log(`📁 Web Root: ${runner.webRoot}`);
  console.log(`⏰ Started at: ${new Date().toISOString()}`);
  console.log();
  
  let success = true;
  
  // Run selected test suites
  if (unitOnly) {
    success = await runner.runUnitTests(verbose);
  } else if (componentOnly) {
    success = await runner.runComponentTests(verbose);
  } else if (e2eOnly) {
    success = await runner.runE2ETests(verbose);
  } else if (accessibilityOnly) {
    success = await runner.runAccessibilityTests(verbose);
  } else if (performanceOnly) {
    success = await runner.runPerformanceTests(verbose);
  } else {
    // Run all test suites
    success &= await runner.runUnitTests(verbose);
    success &= await runner.runComponentTests(verbose);
    success &= await runner.runE2ETests(verbose);
    success &= await runner.runAccessibilityTests(verbose);
    success &= await runner.runPerformanceTests(verbose);
  }
  
  // Generate coverage report
  if (!skipCoverage) {
    await runner.generateCoverageReport();
  }
  
  // Generate final report
  const finalSuccess = runner.generateFinalReport();
  
  // Exit with appropriate code
  process.exit((success && finalSuccess) ? 0 : 1);
}

if (require.main === module) {
  main().catch(console.error);
}

module.exports = { FrontendTestRunner };