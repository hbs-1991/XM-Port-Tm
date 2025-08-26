'use client'

import React from 'react'
import { X, CheckCircle, AlertTriangle, Info, AlertCircle, Clock } from 'lucide-react'
import { WebSocketNotification } from '@/hooks/useProcessingUpdates'
import { Badge } from '@/components/shared/ui'
import { Button } from '@/components/shared/ui'
import { Card, CardContent } from '@/components/shared/ui'
import { format } from 'date-fns'

interface NotificationCenterProps {
  notifications: WebSocketNotification[]
  onClearNotifications: () => void
  isConnected: boolean
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error'
}

const levelConfig = {
  info: {
    icon: Info,
    className: 'bg-blue-50 border-blue-200 text-blue-800',
    iconClass: 'text-blue-500',
    title: 'Info'
  },
  success: {
    icon: CheckCircle,
    className: 'bg-green-50 border-green-200 text-green-800',
    iconClass: 'text-green-500',
    title: 'Success'
  },
  warning: {
    icon: AlertTriangle,
    className: 'bg-yellow-50 border-yellow-200 text-yellow-800',
    iconClass: 'text-yellow-500',
    title: 'Warning'
  },
  error: {
    icon: AlertCircle,
    className: 'bg-red-50 border-red-200 text-red-800',
    iconClass: 'text-red-500',
    title: 'Error'
  }
}

const connectionStatusConfig = {
  connecting: {
    icon: Clock,
    label: 'Connecting...',
    className: 'bg-yellow-100 text-yellow-800'
  },
  connected: {
    icon: CheckCircle,
    label: 'Live Updates Active',
    className: 'bg-green-100 text-green-800'
  },
  disconnected: {
    icon: AlertCircle,
    label: 'Disconnected',
    className: 'bg-gray-100 text-gray-800'
  },
  error: {
    icon: AlertCircle,
    label: 'Connection Error',
    className: 'bg-red-100 text-red-800'
  }
}

const NotificationCenter: React.FC<NotificationCenterProps> = ({
  notifications,
  onClearNotifications,
  isConnected,
  connectionStatus
}) => {
  const statusConfig = connectionStatusConfig[connectionStatus]
  const StatusIcon = statusConfig.icon

  return (
    <div className="fixed top-4 right-4 z-50 max-w-sm w-full">
      {/* Connection Status */}
      <div className="mb-2">
        <Badge variant="secondary" className={statusConfig.className}>
          <StatusIcon className="mr-1 h-3 w-3" />
          {statusConfig.label}
        </Badge>
      </div>

      {/* Notifications */}
      {notifications.length > 0 && (
        <Card className="shadow-lg border">
          <CardContent className="p-3">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-medium text-sm">Recent Updates</h4>
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">
                  {notifications.length} notification{notifications.length !== 1 ? 's' : ''}
                </span>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={onClearNotifications}
                  className="h-6 w-6 p-0"
                >
                  <X className="h-3 w-3" />
                </Button>
              </div>
            </div>

            <div className="space-y-2 max-h-80 overflow-y-auto">
              {notifications.slice(0, 5).map((notification, index) => {
                const config = levelConfig[notification.level]
                const Icon = config.icon

                return (
                  <div
                    key={`${notification.timestamp}-${index}`}
                    className={`p-2 rounded-lg border text-xs ${config.className}`}
                  >
                    <div className="flex items-start gap-2">
                      <Icon className={`h-3 w-3 mt-0.5 flex-shrink-0 ${config.iconClass}`} />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium">{config.title}</p>
                        <p className="mt-1 break-words">{notification.message}</p>
                        <p className="mt-1 text-[10px] opacity-75">
                          {format(new Date(notification.timestamp), 'HH:mm:ss')}
                        </p>
                      </div>
                    </div>
                  </div>
                )
              })}

              {notifications.length > 5 && (
                <div className="text-center pt-2 border-t">
                  <p className="text-xs text-muted-foreground">
                    and {notifications.length - 5} more...
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export default NotificationCenter