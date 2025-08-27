/**
 * Breadcrumb navigation component for dashboard
 */
'use client'

import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { Home, ChevronRight } from 'lucide-react'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/shared/ui/ui/breadcrumb'

const pathToName: Record<string, string> = {
  dashboard: 'Dashboard',
  upload: 'Upload Files',
  history: 'Processing History',
  profile: 'Profile',
  billing: 'Billing & Credits',
}

export default function BreadcrumbNavigation() {
  const pathname = usePathname()
  
  // Split the path and filter out empty parts
  const pathSegments = pathname.split('/').filter(Boolean)
  
  // Don't show breadcrumbs on the main dashboard
  if (pathSegments.length <= 1) {
    return null
  }

  return (
    <div className="mb-4">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link href="/dashboard" className="flex items-center">
                <Home className="h-4 w-4 mr-1" />
                Dashboard
              </Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          
          {pathSegments.slice(1).map((segment, index) => {
            const isLast = index === pathSegments.length - 2
            const href = `/${pathSegments.slice(0, index + 2).join('/')}`
            const name = pathToName[segment] || segment.charAt(0).toUpperCase() + segment.slice(1)
            
            return (
              <div key={segment} className="flex items-center">
                <BreadcrumbSeparator>
                  <ChevronRight className="h-4 w-4" />
                </BreadcrumbSeparator>
                <BreadcrumbItem>
                  {isLast ? (
                    <BreadcrumbPage className="font-medium text-gray-900">
                      {name}
                    </BreadcrumbPage>
                  ) : (
                    <BreadcrumbLink asChild>
                      <Link href={href}>{name}</Link>
                    </BreadcrumbLink>
                  )}
                </BreadcrumbItem>
              </div>
            )
          })}
        </BreadcrumbList>
      </Breadcrumb>
    </div>
  )
}