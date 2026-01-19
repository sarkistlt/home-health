'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  DollarSign,
  Shield,
  Briefcase,
  FileText,
  Users,
  TrendingUp,
  Search,
  LogOut,
  User
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'

const navigationItems = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Revenue', href: '/revenue', icon: DollarSign },
  { name: 'Insurance', href: '/insurance', icon: Shield },
  { name: 'Services', href: '/services', icon: Briefcase },
  { name: 'Claims', href: '/claims', icon: FileText },
  { name: 'Providers', href: '/providers', icon: Users },
  { name: 'Data Explorer', href: '/explorer', icon: Search },
  { name: 'Profitability', href: '/profitability', icon: TrendingUp },
]

export default function Sidebar() {
  const pathname = usePathname()
  const { username, logout } = useAuth()

  return (
    <div className="w-64 bg-white shadow-lg flex flex-col h-full">
      <div className="p-6">
        <h1 className="text-xl font-bold text-gray-900">
          Home Health Analytics
        </h1>
        <p className="text-sm text-gray-600 mt-1">
          Billing & Operations Dashboard
        </p>
      </div>

      <nav className="mt-6 flex-1">
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

      {/* User Info and Logout */}
      <div className="p-4 border-t border-gray-200">
        <div className="flex items-center mb-3">
          <div className="p-2 bg-blue-50 rounded-full">
            <User className="h-4 w-4 text-blue-600" />
          </div>
          <span className="ml-2 text-sm font-medium text-gray-700">
            {username}
          </span>
        </div>
        <button
          onClick={logout}
          className="w-full flex items-center justify-center px-3 py-2 text-sm font-medium text-red-600
                   bg-red-50 hover:bg-red-100 rounded-md transition-colors"
        >
          <LogOut className="h-4 w-4 mr-2" />
          Sign Out
        </button>
      </div>
    </div>
  )
}
