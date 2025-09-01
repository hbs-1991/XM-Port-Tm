/**
 * Enhanced mobile navigation component with improved UX and accessibility
 */
'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useState } from 'react'
import { Menu, Upload, Home, History, User, LogOut, X, Settings, CreditCard, HelpCircle } from 'lucide-react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
  SheetClose
} from '@/components/shared/ui/ui/sheet'
import { Button } from '@/components/shared/ui/button'
import { Badge } from '@/components/shared/ui/badge'
import { Avatar, AvatarFallback } from '@/components/shared/ui/ui/avatar'
import { Separator } from '@/components/shared/ui/ui/separator'

const primaryNavigation = [
  { name: 'Dashboard', href: '/dashboard', icon: Home },
  { name: 'Upload Files', href: '/dashboard/upload', icon: Upload },
  { name: 'Processing History', href: '/dashboard/history', icon: History },
  { name: 'Profile', href: '/dashboard/profile', icon: User },
]

const secondaryNavigation = [
  { name: 'Billing', href: '/dashboard/billing', icon: CreditCard },
  { name: 'Settings', href: '/dashboard/settings', icon: Settings },
  { name: 'Help & Support', href: '/help', icon: HelpCircle, external: true },
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
  const [isOpen, setIsOpen] = useState(false)

  const getUserInitials = () => {
    if (!user) return 'U'
    return `${user.firstName?.[0] || ''}${user.lastName?.[0] || ''}`.toUpperCase()
  }

  const handleLinkClick = () => {
    setIsOpen(false)
  }

  const handleSignOut = async () => {
    setIsOpen(false)
    await onSignOut()
  }

  const isActiveLink = (href: string) => {
    if (href === '/dashboard') {
      return pathname === '/dashboard'
    }
    return pathname.startsWith(href)
  }

  return (
    <div className="md:hidden">
      <Sheet open={isOpen} onOpenChange={setIsOpen}>
        <SheetTrigger asChild>
          <Button 
            variant="ghost" 
            size="icon" 
            className="h-12 w-12 touch-manipulation" 
            aria-label="Open navigation menu"
          >
            <Menu className="h-6 w-6" />
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-80 p-0 flex flex-col">
          {/* Header */}
          <SheetHeader className="border-b p-6">
            <div className="flex items-center justify-between">
              <div>
                <SheetTitle className="text-lg font-semibold">XM-Port</SheetTitle>
                {user && (
                  <p className="text-sm text-muted-foreground mt-1">
                    Welcome, {user.firstName || user.email}
                  </p>
                )}
              </div>
              <SheetClose asChild>
                <Button variant="ghost" size="icon" className="h-10 w-10" aria-label="Close navigation">
                  <X className="h-4 w-4" />
                </Button>
              </SheetClose>
            </div>
            
            {/* Credit Balance */}
            {user && (
              <div className="flex items-center justify-between mt-4 p-3 bg-primary/5 rounded-lg">
                <span className="text-sm font-medium">Credits</span>
                <Badge variant="secondary" className="bg-primary/10">
                  {user.creditsRemaining?.toLocaleString() ?? '0'}
                </Badge>
              </div>
            )}
          </SheetHeader>

          {/* Navigation Items */}
          <div className="flex-1 overflow-y-auto p-6">
            <nav className="space-y-6">
              {/* Primary Navigation */}
              <div>
                <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                  Main
                </h3>
                <div className="space-y-1">
                  {primaryNavigation.map((item) => {
                    const Icon = item.icon
                    const isActive = isActiveLink(item.href)
                    
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        onClick={handleLinkClick}
                        className={`flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium transition-colors min-h-[44px] touch-manipulation ${
                          isActive
                            ? 'bg-primary text-primary-foreground'
                            : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                        }`}
                        aria-current={isActive ? 'page' : undefined}
                      >
                        <Icon className="h-5 w-5 flex-shrink-0" />
                        <span className="flex-1">{item.name}</span>
                      </Link>
                    )
                  })}
                </div>
              </div>

              {/* Secondary Navigation */}
              <div>
                <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                  Account
                </h3>
                <div className="space-y-1">
                  {secondaryNavigation.map((item) => {
                    const Icon = item.icon
                    const isActive = !item.external && isActiveLink(item.href)
                    
                    if (item.external) {
                      return (
                        <a
                          key={item.href}
                          href={item.href}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={handleLinkClick}
                          className="flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors min-h-[44px] touch-manipulation"
                        >
                          <Icon className="h-5 w-5 flex-shrink-0" />
                          <span className="flex-1">{item.name}</span>
                        </a>
                      )
                    }
                    
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        onClick={handleLinkClick}
                        className={`flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium transition-colors min-h-[44px] touch-manipulation ${
                          isActive
                            ? 'bg-primary text-primary-foreground'
                            : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                        }`}
                        aria-current={isActive ? 'page' : undefined}
                      >
                        <Icon className="h-5 w-5 flex-shrink-0" />
                        <span className="flex-1">{item.name}</span>
                      </Link>
                    )
                  })}
                </div>
              </div>
            </nav>
          </div>

          {/* Footer */}
          <div className="border-t p-6">
            <Button
              onClick={handleSignOut}
              disabled={isLoggingOut}
              variant="outline"
              className="w-full justify-start min-h-[44px] touch-manipulation"
            >
              <LogOut className={`h-4 w-4 mr-2 ${isLoggingOut ? 'animate-spin' : ''}`} />
              {isLoggingOut ? 'Signing Out...' : 'Sign Out'}
            </Button>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  )
}