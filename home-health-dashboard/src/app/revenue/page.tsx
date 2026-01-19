'use client'

import { useEffect, useState } from 'react'
import { ArrowUpIcon, ArrowDownIcon, Search } from 'lucide-react'
import { apiFetch } from '@/lib/api'

interface RevenueData {
  'Patient Name': string
  'Claim Code': string
  'Cycle Start': string
  'Cycle End': string
  'Insurance': string
  'Total Amount Billed': number
  'Expected Payment': number
  'Actual Payment Received': number
  'Remaining Balance': number
  'Net Adjustment': number
  'Payment Requested At': string
  'Payment Received At': string
  'Days to Payment': number
}

export default function RevenuePage() {
  const [data, setData] = useState<RevenueData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sortField, setSortField] = useState<keyof RevenueData>('Total Amount Billed')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await apiFetch('/analytics/revenue-by-claim')
        if (!response.ok) throw new Error('Failed to fetch revenue data')
        const revenueData = await response.json()
        setData(revenueData)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  const handleSort = (field: keyof RevenueData) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
  }

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount)

  const filteredData = data.filter(item =>
    item['Patient Name'].toLowerCase().includes(searchTerm.toLowerCase()) ||
    item['Insurance'].toLowerCase().includes(searchTerm.toLowerCase()) ||
    item['Claim Code'].toString().includes(searchTerm)
  )

  const sortedData = [...filteredData].sort((a, b) => {
    let aValue = a[sortField]
    let bValue = b[sortField]

    if (typeof aValue === 'string') {
      aValue = aValue.toLowerCase()
      bValue = (bValue as string).toLowerCase()
    }

    if (sortDirection === 'asc') {
      return aValue < bValue ? -1 : aValue > bValue ? 1 : 0
    } else {
      return aValue > bValue ? -1 : aValue < bValue ? 1 : 0
    }
  })

  // Calculate summary statistics
  const totalBilled = data.reduce((sum, item) => sum + item['Total Amount Billed'], 0)
  const totalCollected = data.reduce((sum, item) => sum + item['Actual Payment Received'], 0)
  const totalOutstanding = data.reduce((sum, item) => sum + item['Remaining Balance'], 0)
  const collectionRate = totalBilled > 0 ? (totalCollected / totalBilled) * 100 : 0

  if (loading) {
    return (
      <div className="p-8">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/3 mb-6"></div>
          <div className="bg-white rounded-lg shadow h-96"></div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h3 className="text-red-800 font-medium">Error Loading Revenue Data</h3>
          <p className="text-red-600 text-sm mt-1">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Revenue by Claim Analysis</h1>
        <p className="text-gray-600 mt-2">
          Detailed breakdown of claims revenue, payments, and outstanding balances
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-600">Total Billed</h3>
          <p className="text-2xl font-bold text-gray-900">{formatCurrency(totalBilled)}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-600">Total Collected</h3>
          <p className="text-2xl font-bold text-green-600">{formatCurrency(totalCollected)}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-600">Outstanding Balance</h3>
          <p className="text-2xl font-bold text-red-600">{formatCurrency(totalOutstanding)}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-600">Collection Rate</h3>
          <p className="text-2xl font-bold text-blue-600">{collectionRate.toFixed(1)}%</p>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium text-gray-900">Claims Revenue Data</h2>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <input
                type="text"
                placeholder="Search patients, insurance, or claim codes..."
                className="pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {[
                  { key: 'Patient Name', label: 'Patient Name' },
                  { key: 'Claim Code', label: 'Claim Code' },
                  { key: 'Insurance', label: 'Insurance' },
                  { key: 'Total Amount Billed', label: 'Amount Billed' },
                  { key: 'Expected Payment', label: 'Expected Payment' },
                  { key: 'Actual Payment Received', label: 'Payment Received' },
                  { key: 'Remaining Balance', label: 'Remaining Balance' },
                  { key: 'Net Adjustment', label: 'Net Adjustment' }
                ].map((column) => (
                  <th
                    key={column.key}
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort(column.key as keyof RevenueData)}
                  >
                    <div className="flex items-center">
                      {column.label}
                      {sortField === column.key && (
                        sortDirection === 'asc' ?
                          <ArrowUpIcon className="ml-1 h-4 w-4" /> :
                          <ArrowDownIcon className="ml-1 h-4 w-4" />
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {sortedData.map((item, index) => (
                <tr key={index} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {item['Patient Name']}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {item['Claim Code']}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      {item['Insurance']}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-medium">
                    {formatCurrency(item['Total Amount Billed'])}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatCurrency(item['Expected Payment'])}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-green-600 font-medium">
                    {formatCurrency(item['Actual Payment Received'])}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <span className={item['Remaining Balance'] > 0 ? 'text-red-600' : 'text-gray-900'}>
                      {formatCurrency(item['Remaining Balance'])}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatCurrency(item['Net Adjustment'])}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Table Footer with Results Count */}
        <div className="bg-gray-50 px-6 py-3 border-t border-gray-200">
          <p className="text-sm text-gray-700">
            Showing {sortedData.length} of {data.length} claims
            {searchTerm && ` (filtered by "${searchTerm}")`}
          </p>
        </div>
      </div>
    </div>
  )
}