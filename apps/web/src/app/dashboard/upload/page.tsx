/**
 * File upload page - reuses existing FileUpload component
 */
'use client'

import { FileUpload } from '@/components/dashboard/upload'

export default function UploadPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Upload Files</h1>
        <p className="mt-1 text-sm text-gray-500">
          Upload your Excel or CSV files for HS code matching and XML generation
        </p>
      </div>
      <FileUpload />
    </div>
  )
}