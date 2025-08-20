/**
 * Zod validation schemas
 */
import { z } from 'zod';

export const LoginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

export const RegisterSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/, 'Password must contain uppercase, lowercase, and number'),
  name: z.string().min(2, 'Name must be at least 2 characters'),
});

export const FileUploadSchema = z.object({
  filename: z.string().min(1, 'Filename is required'),
  fileSize: z.number().max(10 * 1024 * 1024, 'File size cannot exceed 10MB'),
  fileType: z.string().refine(
    (type) => ['application/pdf', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel', 'text/csv'].includes(type),
    'Invalid file type'
  ),
});