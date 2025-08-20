/**
 * Example utility function tests
 */
import { describe, it, expect } from '@jest/globals'
import { formatFileSize, isValidEmail } from '@xm-port/shared'

describe('Utility Functions', () => {
  describe('formatFileSize', () => {
    it('formats bytes correctly', () => {
      expect(formatFileSize(0)).toBe('0 Bytes')
      expect(formatFileSize(1024)).toBe('1 KB')
      expect(formatFileSize(1024 * 1024)).toBe('1 MB')
      expect(formatFileSize(1024 * 1024 * 1024)).toBe('1 GB')
    })
  })

  describe('isValidEmail', () => {
    it('validates email addresses correctly', () => {
      expect(isValidEmail('test@example.com')).toBe(true)
      expect(isValidEmail('invalid-email')).toBe(false)
      expect(isValidEmail('test@')).toBe(false)
      expect(isValidEmail('@example.com')).toBe(false)
    })
  })
})