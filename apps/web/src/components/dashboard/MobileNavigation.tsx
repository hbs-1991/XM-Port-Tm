/**
 * Enhanced mobile navigation component with Sheet component
 */
'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Menu, Upload, Home, History, User, LogOut, X } from 'lucide-react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/shared/ui/ui/sheet'
import { Button } from '@/components/shared/ui/button'
import { Badge } from '@/components/shared/ui/badge'
import { Avatar, AvatarFallback } from '@/components/shared/ui/ui/avatar'
import { Separator } from '@/components/shared/ui/ui/separator'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: Home },
  { name: 'Upload Files', href: '/dashboard/upload', icon: Upload },
  { name: 'Processing History', href: '/dashboard/history', icon: History },
  { name: 'Profile', href: '/dashboard/profile', icon: User },
]

interface MobileNavigationProps {
  user: any
  onSignOut: () => void
  isLoggingOut: boolean
}

export default function MobileNavigation({ 
  user, 
  onSignOut, 
  isLoggingOut 
}: MobileNavigationProps) {
  const pathname = usePathname()

  const getUserInitials = () => {
    if (!user) return 'U'
    return `${user.firstName?.[0] || ''}${user.lastName?.[0] || ''}`.toUpperCase()
  }

  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" className="md:hidden">
          <Menu className="h-6 w-6" />
          <span className="sr-only">Open navigation menu</span>
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-80 px-0">
        <SheetHeader className="px-6 pb-4">
          <SheetTitle className="text-left text-xl font-bold text-gray-900">
            XM-Port
          </SheetTitle>
        </SheetHeader>
        
        {/* User Profile Section */}
        <div className="px-6 pb-4">
          <div className="flex items-center space-x-3 p-3 rounded-lg bg-gray-50">
            <Avatar className="h-10 w-10">
              <AvatarFallback className="bg-blue-500 text-white">
                {getUserInitials()}
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-gray-900 truncate">
                {user?.firstName} {user?.lastName}
              </p>
              <p className="text-xs text-gray-500 truncate">{user?.email}</p>
            </div>
          </div>
          
          {/* Credit Balance */}
          {user && (
            <div className="mt-3 p-3 rounded-lg bg-blue-50 border border-blue-100">
              <div className="flex items-center justify-between">
                <span className="text-sm text-blue-700 font-medium">Credits</span>
                <Badge variant="outline" className="bg-white">
                  {user.creditsRemaining?.toLocaleString() ?? '0'}
                </Badge>
              </div>
            </div>
          )}
        </div>

        <Separator />

        {/* Navigation Links */}
        <nav className="flex-1 px-6 py-4">
          <div className="space-y-1">
            {navigation.map((item) => {
              const isActive = pathname === item.href
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`group flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-blue-100 text-blue-700 border border-blue-200'
                      : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                  }`}
                >
                  <item.icon
                    className={`mr-3 h-5 w-5 flex-shrink-0 ${
                      isActive ? 'text-blue-700' : 'text-gray-400 group-hover:text-gray-600'
                    }`}
                  />
                  {item.name}
                </Link>
              )
            })}
          </div>
        </nav>

        <Separator />

        {/* Bottom Actions */}
        <div className="p-6">
          <Button
            variant="ghost"
            onClick={onSignOut}
            disabled={isLoggingOut}
            className="w-full justify-start text-red-600 hover:text-red-700 hover:bg-red-50"
          >
            <LogOut className={`mr-3 h-4 w-4 ${isLoggingOut ? 'animate-spin' : ''}`} />
            {isLoggingOut ? 'Signing Out...' : 'Sign Out'}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  )
}