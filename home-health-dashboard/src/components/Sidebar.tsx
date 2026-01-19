'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  TrendingUp,
  Search
} from 'lucide-react'

const navigationItems = [
  { name: 'Data Explorer', href: '/explorer', icon: Search },
  { name: 'Profitability', href: '/profitability', icon: TrendingUp },
]

export default function Sidebar() {
  const pathname = usePathname()

  return (
    <div className="w-64 bg-white shadow-lg">
      <div className="p-6">
        <h1 className="text-xl font-bold text-gray-900">
          Home Health Analytics
        </h1>
        <p className="text-sm text-gray-600 mt-1">
          Billing & Operations Dashboard
        </p>
      </div>

      <nav className="mt-6">
        <div className="px-3">
          {navigationItems.map((item) => {
            const isActive = pathname === item.href
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`group flex items-center px-3 py-2 text-sm font-medium rounded-md mb-1 transition-colors ${
                  isActive
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                }`}
              >
                <item.icon
                  className={`mr-3 h-5 w-5 ${
                    isActive ? 'text-blue-500' : 'text-gray-400 group-hover:text-gray-500'
                  }`}
                />
                {item.name}
              </Link>
            )
          })}
        </div>
      </nav>

      <div className="absolute bottom-6 left-6 right-6">
        <div className="bg-blue-50 rounded-lg p-4">
          <h3 className="text-sm font-medium text-blue-900">
            Last Updated
          </h3>
          <p className="text-xs text-blue-700 mt-1">
            {new Date().toLocaleDateString()}
          </p>
        </div>
      </div>
    </div>
  )
}