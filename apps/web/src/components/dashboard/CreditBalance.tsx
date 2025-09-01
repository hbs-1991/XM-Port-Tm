/**
 * Credit Balance component showing user credit information and usage statistics
 */
'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle 
} from '@/components/shared/ui/card'
import { Badge } from '@/components/shared/ui/badge'
import { Button } from '@/components/shared/ui/button'
import { Progress } from '@/components/shared/ui/progress'
import { 
  CreditCard, 
  TrendingUp, 
  TrendingDown, 
  AlertTriangle,
  Plus,
  Info
} from 'lucide-react'
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from '@/components/shared/ui/alert'
// TODO: Add tooltip component when available
// import {
//   Tooltip,
//   TooltipContent,
//   TooltipProvider,
//   TooltipTrigger,
// } from '@/components/shared/ui/tooltip'
import type { CreditBalance as CreditBalanceType } from '@shared/types'

interface CreditBalanceProps {
  creditBalance?: CreditBalanceType
  loading?: boolean
  className?: string
}

export function CreditBalance({ 
  creditBalance, 
  loading = false, 
  className = '' 
}: CreditBalanceProps) {
  const { user } = useAuth()
  const [displayBalance, setDisplayBalance] = useState<CreditBalanceType | null>(null)

  useEffect(() => {
    if (creditBalance) {
      setDisplayBalance(creditBalance)
    } else if (user) {
      // Fallback to user data if creditBalance prop not provided
      const total = user.creditsRemaining + user.creditsUsedThisMonth
      setDisplayBalance({
        remaining: user.creditsRemaining,
        total,
        usedThisMonth: user.creditsUsedThisMonth,
        percentageUsed: total > 0 ? (user.creditsUsedThisMonth / total) * 100 : 0,
        subscriptionTier: user.subscriptionTier
      })
    }
  }, [creditBalance, user])

  if (loading) {
    return (
      <Card className={`animate-pulse ${className}`}>
        <CardHeader>
          <div className="h-4 bg-gray-300 rounded w-1/2 mb-2"></div>
          <div className="h-3 bg-gray-300 rounded w-3/4"></div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="h-6 bg-gray-300 rounded"></div>
          <div className="h-3 bg-gray-300 rounded"></div>
          <div className="h-8 bg-gray-300 rounded w-1/3"></div>
        </CardContent>
      </Card>
    )
  }

  if (!displayBalance) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="h-5 w-5" />
            Credit Balance
          </CardTitle>
          <CardDescription>Unable to load credit information</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  const isLowBalance = (displayBalance.remaining ?? 0) < 100
  const isVeryLowBalance = (displayBalance.remaining ?? 0) < 25
  const usagePercentage = Math.min(displayBalance.percentageUsed ?? 0, 100)

  const getTierColor = (tier: string | undefined) => {
    if (!tier) return 'bg-gray-100 text-gray-800 border-gray-200'
    switch (tier.toUpperCase()) {
      case 'FREE':
        return 'bg-gray-100 text-gray-800 border-gray-200'
      case 'BASIC':
        return 'bg-blue-100 text-blue-800 border-blue-200'
      case 'PREMIUM':
        return 'bg-purple-100 text-purple-800 border-purple-200'
      case 'ENTERPRISE':
        return 'bg-amber-100 text-amber-800 border-amber-200'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const getTierLabel = (tier: string | undefined) => {
    if (!tier) return 'Unknown'
    return tier.charAt(0).toUpperCase() + tier.slice(1).toLowerCase()
  }

  return (
    <div className={`space-y-4 ${className}`}>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="h-5 w-5" />
            Credit Balance
            <div className="relative" title="Credits are used to process your files and match HS codes">
              <Info className="h-4 w-4 text-gray-400 cursor-help" />
            </div>
          </CardTitle>
          <CardDescription>
            Current balance and monthly usage for your {getTierLabel(displayBalance.subscriptionTier)} plan
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Current Balance */}
          <div className="text-center">
            <div className="text-3xl font-bold text-gray-900">
              {(displayBalance.remaining ?? 0).toLocaleString()}
            </div>
            <div className="text-sm text-gray-500 mt-1">
              Credits Available
            </div>
          </div>

          {/* Usage Progress */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Monthly Usage</span>
              <span className="font-medium">
                {(displayBalance.usedThisMonth ?? 0).toLocaleString()} / {(displayBalance.total ?? 0).toLocaleString()}
              </span>
            </div>
            <Progress 
              value={usagePercentage} 
              className="h-2"
            />
            <div className="text-xs text-gray-500 text-center">
              {usagePercentage.toFixed(1)}% used this month
            </div>
          </div>

          {/* Subscription Tier */}
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium text-gray-600">Plan</span>
            <Badge variant="outline" className={getTierColor(displayBalance.subscriptionTier)}>
              {getTierLabel(displayBalance.subscriptionTier)}
            </Badge>
          </div>

          {/* Action Button */}
          <Button className="w-full" variant="outline">
            <Plus className="h-4 w-4 mr-2" />
            Purchase Credits
          </Button>
        </CardContent>
      </Card>

      {/* Low Balance Alert */}
      {(isLowBalance || isVeryLowBalance) && (
        <Alert variant={isVeryLowBalance ? "destructive" : "default"}>
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>
            {isVeryLowBalance ? 'Critical Low Balance' : 'Low Credit Balance'}
          </AlertTitle>
          <AlertDescription>
            {isVeryLowBalance ? (
              <>You have very few credits remaining. Consider purchasing more credits to continue processing files.</>
            ) : (
              <>Your credit balance is running low. You may want to purchase additional credits soon.</>
            )}
          </AlertDescription>
        </Alert>
      )}
    </div>
  )
}

export default CreditBalance