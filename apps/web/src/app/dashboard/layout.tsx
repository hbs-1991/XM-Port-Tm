/**
 * Dashboard layout with authentication guard and responsive sidebar
 */
'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { AuthGuard } from '@/components/shared/AuthGuard'
import { useAuth } from '@/hooks/useAuth'
import { useRouter } from 'next/navigation'
import {
  Home,
  Upload,
  History,
  User,
  CreditCard,
  Menu,
  X,
  LogOut,
  ChevronDown,
} from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/shared/ui/ui/dropdown-menu'
import { Button } from '@/components/shared/ui/button'
import { Avatar, AvatarFallback } from '@/components/shared/ui/ui/avatar'
import { Badge } from '@/components/shared/ui/badge'
import NotificationCenter from '@/components/shared/NotificationCenter'
import { useProcessingUpdates } from '@/hooks/useProcessingUpdates'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: Home },
  { name: 'Upload Files', href: '/dashboard/upload', icon: Upload },
  { name: 'Processing History', href: '/dashboard/history', icon: History },
  { name: 'Profile', href: '/dashboard/profile', icon: User },
]

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const pathname = usePathname()
  const router = useRouter()
  const { user, logout, isLoading } = useAuth()
  const { notifications, clearNotifications, isConnected, connectionStatus } = useProcessingUpdates()

  const handleSignOut = async () => {
    setIsLoggingOut(true)
    try {
      await logout()
      // Navigate to home page after successful logout
      router.push('/')
    } catch (error) {
      console.error('Logout failed:', error)
      // Even if logout fails, try to redirect to home
      router.push('/')
    } finally {
      setIsLoggingOut(false)
    }
  }

  const getUserInitials = () => {
    if (!user) return 'U'
    return `${user.firstName?.[0] || ''}${user.lastName?.[0] || ''}`.toUpperCase()
  }

  return (
    <AuthGuard>
      <div className="min-h-screen bg-gray-50">
        {/* Mobile sidebar backdrop */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-40 bg-gray-600 bg-opacity-75 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Mobile sidebar */}
        <div
          className={`fixed inset-y-0 left-0 z-50 w-64 transform bg-white shadow-lg transition-transform duration-300 ease-in-out lg:hidden ${
            sidebarOpen ? 'translate-x-0' : '-translate-x-full'
          }`}
        >
          <div className="flex h-16 items-center justify-between px-4">
            <h2 className="text-xl font-semibold text-gray-900">XM-Port</h2>
            <button
              onClick={() => setSidebarOpen(false)}
              className="text-gray-500 hover:text-gray-700"
            >
              <X className="h-6 w-6" />
            </button>
          </div>
          <nav className="mt-5 space-y-1 px-2">
            {navigation.map((item) => {
              const isActive = pathname === item.href
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  onClick={() => setSidebarOpen(false)}
                  className={`group flex items-center rounded-md px-2 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                  }`}
                >
                  <item.icon
                    className={`mr-3 h-5 w-5 flex-shrink-0 ${
                      isActive ? 'text-blue-700' : 'text-gray-400 group-hover:text-gray-500'
                    }`}
                  />
                  {item.name}
                </Link>
              )
            })}
          </nav>
        </div>

        {/* Desktop sidebar */}
        <div className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col">
          <div className="flex min-h-0 flex-1 flex-col border-r border-gray-200 bg-white">
            <div className="flex h-16 flex-shrink-0 items-center px-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900">XM-Port</h2>
            </div>
            <nav className="mt-5 flex-1 space-y-1 px-2">
              {navigation.map((item) => {
                const isActive = pathname === item.href
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={`group flex items-center rounded-md px-2 py-2 text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-blue-50 text-blue-700'
                        : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                    }`}
                  >
                    <item.icon
                      className={`mr-3 h-5 w-5 flex-shrink-0 ${
                        isActive ? 'text-blue-700' : 'text-gray-400 group-hover:text-gray-500'
                      }`}
                    />
                    {item.name}
                  </Link>
                )
              })}
            </nav>
          </div>
        </div>

        {/* Main content area */}
        <div className="lg:pl-64">
          {/* Top header */}
          <header className="sticky top-0 z-30 bg-white shadow">
            <div className="px-4 sm:px-6 lg:px-8">
              <div className="flex h-16 items-center justify-between">
                {/* Mobile menu button */}
                <button
                  onClick={() => setSidebarOpen(true)}
                  className="text-gray-500 hover:text-gray-700 lg:hidden"
                >
                  <Menu className="h-6 w-6" />
                </button>

                {/* Credit balance display */}
                <div className="flex items-center space-x-4">
                  {user && (
                    <div className="flex items-center space-x-2">
                      <CreditCard className="h-5 w-5 text-gray-400" />
                      <div className="text-sm">
                        <span className="text-gray-500">Credits:</span>
                        <Badge variant="outline" className="ml-2">
                          {user.creditsRemaining?.toLocaleString() ?? '0'}
                        </Badge>
                      </div>
                    </div>
                  )}
                </div>

                {/* User profile dropdown */}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      className="flex items-center space-x-3 hover:bg-gray-50"
                    >
                      <Avatar className="h-8 w-8">
                        <AvatarFallback className="bg-blue-500 text-white">
                          {getUserInitials()}
                        </AvatarFallback>
                      </Avatar>
                      <div className="hidden text-left sm:block">
                        <p className="text-sm font-medium text-gray-700">
                          {user?.firstName} {user?.lastName}
                        </p>
                        <p className="text-xs text-gray-500">{user?.email}</p>
                      </div>
                      <ChevronDown className="h-4 w-4 text-gray-400" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-56">
                    <DropdownMenuLabel>
                      <div>
                        <p className="text-sm font-medium">
                          {user?.firstName} {user?.lastName}
                        </p>
                        <p className="text-xs text-gray-500">{user?.email}</p>
                        {user?.companyName && (
                          <p className="text-xs text-gray-500 mt-1">{user.companyName}</p>
                        )}
                      </div>
                    </DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem asChild>
                      <Link href="/dashboard/profile" className="cursor-pointer">
                        <User className="mr-2 h-4 w-4" />
                        Profile Settings
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuItem asChild>
                      <Link href="/dashboard/billing" className="cursor-pointer">
                        <CreditCard className="mr-2 h-4 w-4" />
                        Billing & Credits
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={handleSignOut}
                      disabled={isLoggingOut || isLoading}
                      className="cursor-pointer text-red-600 focus:text-red-600 disabled:opacity-50"
                    >
                      <LogOut className={`mr-2 h-4 w-4 ${isLoggingOut ? 'animate-spin' : ''}`} />
                      {isLoggingOut ? 'Signing Out...' : 'Sign Out'}
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
          </header>

          {/* Page content */}
          <main className="flex-1">
            <div className="px-4 py-6 sm:px-6 lg:px-8">{children}</div>
          </main>
        </div>

        {/* Notification Center - Fixed positioning */}
        <NotificationCenter
          notifications={notifications}
          onClearNotifications={clearNotifications}
          isConnected={isConnected}
          connectionStatus={connectionStatus}
        />
      </div>
    </AuthGuard>
  )
}