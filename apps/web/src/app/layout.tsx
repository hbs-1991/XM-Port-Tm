/**
 * Root layout for XM-Port application
 */
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { Providers } from './providers'

import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'XM-Port - AI-Powered Customs Documentation',
  description: 'Transform your customs documentation process with AI-powered automation',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  )
}