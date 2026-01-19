'use client'

import { useEffect, useState } from 'react'
import { ArrowUpIcon, ArrowDownIcon, Search, UserCheck, Users, DollarSign, Activity } from 'lucide-react'

interface ProviderData {
  'Provider Name': string
  'Service Type': string
  'Total Visits': number
  'Total Cost': number
  'Avg Cost per Visit': number
  '# of Patients Served': number
  'Avg Cost per Patient': number
}

export default function ProvidersPage() {
  const [data, setData] = useState<ProviderData[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sortField, setSortField] = useState<keyof ProviderData>('Total Cost')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    const fetchData = async () => {
      try {
        const { apiFetch } = await import('@/lib/api')
        const response = await apiFetch('/analytics/provider-performance')
        if (!response.ok) throw new Error('Failed to fetch provider performance data')
        const providerData = await response.json()
        setData(providerData)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  const handleSort = (field: keyof ProviderData) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
  }

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(amount)

  const formatCurrencyDetailed = (amount: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount)

  if (loading) {
    return (
      <div className="p-8">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/3 mb-6"></div>
          <div className="grid grid-cols-4 gap-4 mb-6">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-24 bg-gray-200 rounded"></div>
            ))}
          </div>
          <div className="bg-white rounded-lg shadow h-96"></div>
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h3 className="text-red-800 font-medium">Error Loading Provider Performance Data</h3>
          <p className="text-red-600 text-sm mt-1">{error || 'No data available'}</p>
        </div>
      </div>
    )
  }

  // Calculate summary metrics
  const uniqueProviders = new Set(data.map(d => d['Provider Name'])).size
  const totalVisits = data.reduce((sum, d) => sum + d['Total Visits'], 0)
  const totalCost = data.reduce((sum, d) => sum + d['Total Cost'], 0)
  const totalPatients = data.reduce((sum, d) => sum + d['# of Patients Served'], 0)
  const avgCostPerVisit = totalVisits > 0 ? totalCost / totalVisits : 0

  const filteredData = data.filter(item =>
    item['Provider Name'].toLowerCase().includes(searchTerm.toLowerCase()) ||
    item['Service Type'].toLowerCase().includes(searchTerm.toLowerCase())
  )

  const sortedData = [...filteredData].sort((a, b) => {
    const aValue = a[sortField]
    const bValue = b[sortField]

    if (typeof aValue === 'string') {
      return sortDirection === 'asc'
        ? aValue.localeCompare(bValue as string)
        : (bValue as string).localeCompare(aValue)
    }

    return sortDirection === 'asc'
      ? (aValue as number) - (bValue as number)
      : (bValue as number) - (aValue as number)
  })

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Provider Performance</h1>
        <p className="text-gray-600 mt-2">
          Caregiver productivity and cost metrics by service type
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-600">Total Providers</h3>
            <UserCheck className="h-5 w-5 text-blue-500" />
          </div>
          <p className="text-2xl font-bold text-blue-600 mt-2">{uniqueProviders}</p>
          <p className="text-xs text-gray-500 mt-1">Unique caregivers</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-600">Total Visits</h3>
            <Activity className="h-5 w-5 text-green-500" />
          </div>
          <p className="text-2xl font-bold text-green-600 mt-2">{totalVisits.toLocaleString()}</p>
          <p className="text-xs text-gray-500 mt-1">All service visits</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-600">Total Cost</h3>
            <DollarSign className="h-5 w-5 text-red-500" />
          </div>
          <p className="text-2xl font-bold text-red-600 mt-2">{formatCurrency(totalCost)}</p>
          <p className="text-xs text-gray-500 mt-1">Avg {formatCurrencyDetailed(avgCostPerVisit)}/visit</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-600">Patients Served</h3>
            <Users className="h-5 w-5 text-purple-500" />
          </div>
          <p className="text-2xl font-bold text-purple-600 mt-2">{totalPatients.toLocaleString()}</p>
          <p className="text-xs text-gray-500 mt-1">Total patient assignments</p>
        </div>
      </div>

      {/* Data Table */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-600">
              Provider performance breakdown by service type
            </p>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <input
                type="text"
                placeholder="Search providers..."
                className="pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {[
                  { key: 'Provider Name', label: 'Provider' },
                  { key: 'Service Type', label: 'Service Type' },
                  { key: 'Total Visits', label: 'Visits' },
                  { key: 'Total Cost', label: 'Total Cost' },
                  { key: 'Avg Cost per Visit', label: 'Avg Cost/Visit' },
                  { key: '# of Patients Served', label: 'Patients' },
                  { key: 'Avg Cost per Patient', label: 'Avg Cost/Patient' }
                ].map((column) => (
                  <th
                    key={column.key}
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort(column.key as keyof ProviderData)}
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
                    {item['Provider Name']}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                    <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                      {item['Service Type']}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {item['Total Visits'].toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-red-600 font-medium">
                    {formatCurrency(item['Total Cost'])}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                    {formatCurrencyDetailed(item['Avg Cost per Visit'])}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {item['# of Patients Served']}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                    {formatCurrencyDetailed(item['Avg Cost per Patient'])}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="bg-gray-50 px-6 py-3 border-t border-gray-200">
          <p className="text-sm text-gray-600">
            Showing {sortedData.length} of {data.length} provider-service combinations
          </p>
        </div>
      </div>
    </div>
  )
}
