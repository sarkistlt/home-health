'use client'

import { useEffect, useState } from 'react'
import { ArrowUpIcon, ArrowDownIcon, Search, DollarSign } from 'lucide-react'

interface ServiceCostData {
  'Service Type': string
  'Provider': string
  'Total Cost': number
  'Total Hours': number
  'Cost per Hour': number
  'Total Visits': number
  'Cost per Visit': number
  'Revenue Generated': number
  'Profit Margin': number
}

export default function ServicesPage() {
  const [data, setData] = useState<ServiceCostData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sortField, setSortField] = useState<keyof ServiceCostData>('Total Cost')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    const fetchData = async () => {
      try {
        const { apiFetch } = await import('@/lib/api')
        const response = await apiFetch('/analytics/service-costs')
        if (!response.ok) throw new Error('Failed to fetch service costs data')
        const serviceCostData = await response.json()
        setData(serviceCostData)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  const handleSort = (field: keyof ServiceCostData) => {
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
    item['Service Type'].toLowerCase().includes(searchTerm.toLowerCase()) ||
    item['Provider'].toLowerCase().includes(searchTerm.toLowerCase())
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
  const totalCost = data.reduce((sum, item) => sum + item['Total Cost'], 0)
  const totalRevenue = data.reduce((sum, item) => sum + item['Revenue Generated'], 0)
  const totalHours = data.reduce((sum, item) => sum + (item['Total Hours'] || 0), 0)
  const totalVisits = data.reduce((sum, item) => sum + (item['Total Visits'] || 0), 0)
  const avgProfitMargin = data.length > 0 ? data.reduce((sum, item) => sum + (item['Profit Margin'] || 0), 0) / data.length : 0

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
          <h3 className="text-red-800 font-medium">Error Loading Service Costs Data</h3>
          <p className="text-red-600 text-sm mt-1">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Service Costs Analysis</h1>
        <p className="text-gray-600 mt-2">
          Breakdown of costs by service type and provider performance
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-600">Total Costs</h3>
          <p className="text-2xl font-bold text-red-600">{formatCurrency(totalCost)}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-600">Total Revenue</h3>
          <p className="text-2xl font-bold text-green-600">{formatCurrency(totalRevenue)}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-600">Total Hours</h3>
          <p className="text-2xl font-bold text-blue-600">{totalHours.toFixed(1)}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-600">Total Visits</h3>
          <p className="text-2xl font-bold text-purple-600">{totalVisits}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-600">Avg Profit Margin</h3>
          <p className="text-2xl font-bold text-orange-600">{avgProfitMargin.toFixed(1)}%</p>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium text-gray-900">Service Cost Data</h2>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <input
                type="text"
                placeholder="Search services or providers..."
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
                  { key: 'Service Type', label: 'Service Type' },
                  { key: 'Provider', label: 'Provider' },
                  { key: 'Total Cost', label: 'Total Cost' },
                  { key: 'Total Hours', label: 'Total Hours' },
                  { key: 'Cost per Hour', label: 'Cost/Hour' },
                  { key: 'Total Visits', label: 'Visits' },
                  { key: 'Revenue Generated', label: 'Revenue' },
                  { key: 'Profit Margin', label: 'Profit Margin' }
                ].map((column) => (
                  <th
                    key={column.key}
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort(column.key as keyof ServiceCostData)}
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
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      {item['Service Type']}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {item['Provider']}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-red-600 font-medium">
                    {formatCurrency(item['Total Cost'])}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {(item['Total Hours'] || 0).toFixed(1)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatCurrency(item['Cost per Hour'] || 0)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {item['Total Visits']}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-green-600 font-medium">
                    {formatCurrency(item['Revenue Generated'])}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <span className={(item['Profit Margin'] || 0) >= 0 ? 'text-green-600' : 'text-red-600'}>
                      {(item['Profit Margin'] || 0).toFixed(1)}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Table Footer with Results Count */}
        <div className="bg-gray-50 px-6 py-3 border-t border-gray-200">
          <p className="text-sm text-gray-700">
            Showing {sortedData.length} of {data.length} service records
            {searchTerm && ` (filtered by "${searchTerm}")`}
          </p>
        </div>
      </div>
    </div>
  )
}