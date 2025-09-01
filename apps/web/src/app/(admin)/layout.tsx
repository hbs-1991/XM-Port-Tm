/**
 * Admin layout with role-based authentication guard
 */
import { AuthGuard } from '@/components/shared/AuthGuard'

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <AuthGuard allowedRoles={['ADMIN', 'PROJECT_OWNER']} fallbackUrl="/unauthorized">
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow border-b border-red-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex items-center">
                <h1 className="text-xl font-semibold text-gray-900">XM-Port Admin Panel</h1>
              </div>
              <div className="flex items-center">
                <span className="text-sm text-red-600 bg-red-100 px-2 py-1 rounded">Admin</span>
              </div>
            </div>
          </div>
        </header>
        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          {children}
        </main>
      </div>
    </AuthGuard>
  )
}