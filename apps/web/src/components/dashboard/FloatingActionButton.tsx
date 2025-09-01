/**
 * Floating Action Button for primary actions on mobile
 */
'use client'

import Link from 'next/link'
import { Upload, Plus } from 'lucide-react'
import { Button } from '@/components/shared/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/shared/ui/ui/tooltip'

interface FloatingActionButtonProps {
  className?: string
}

export default function FloatingActionButton({ className = '' }: FloatingActionButtonProps) {
  return (
    <div className={`fixed bottom-6 right-6 z-50 md:hidden ${className}`}>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              size="lg"
              asChild
              className="h-14 w-14 rounded-full shadow-lg hover:shadow-xl transition-shadow bg-blue-600 hover:bg-blue-700"
            >
              <Link href="/dashboard/upload" aria-label="Upload files">
                <Upload className="h-6 w-6" />
              </Link>
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            <p>Upload Files</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  )
}