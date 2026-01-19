'use client'

import { useEffect, useState } from 'react'
import { ArrowUpIcon, ArrowDownIcon, Search } from 'lucide-react'

interface CodePerformanceData {
  'Claim Code': string
  'Total Claims': number
  'Avg Billed Amount': number
  'Avg Expected Payment': number
  'Avg Actual Payment': number
  'Total Received': number
  'Avg Adjustment': number
  'Avg % Collected': number
}

export default function ClaimsPage() {
  const [data, setData] = useState<CodePerformanceData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sortField, setSortField] = useState<keyof CodePerformanceData>('Total Claims')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    const fetchData = async () => {
      try {
        const { apiFetch } = await import('@/lib/api')
        const response = await apiFetch('/analytics/code-performance')
        if (!response.ok) throw new Error('Failed to fetch claims data')
        const codeData = await response.json()
        setData(codeData)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  const handleSort = (field: keyof CodePerformanceData) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
  }

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount)

  const formatPercent = (value: number) => `${value.toFixed(1)}%`

  const filteredData = data.filter(item =>
    item['Claim Code'].toString().toLowerCase().includes(searchTerm.toLowerCase())
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
  const totalClaims = data.reduce((sum, item) => sum + item['Total Claims'], 0)
  const totalReceived = data.reduce((sum, item) => sum + item['Total Received'], 0)
  const avgCollectionRate = data.length > 0
    ? data.reduce((sum, item) => sum + item['Avg % Collected'], 0) / data.length
    : 0
  const uniqueCodes = data.length

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

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h3 className="text-red-800 font-medium">Error Loading Claims Data</h3>
          <p className="text-red-600 text-sm mt-1">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Claims Analysis</h1>
        <p className="text-gray-600 mt-2">
          Claim code success rates and collection analysis
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-600">Total Claims</h3>
          <p className="text-2xl font-bold text-gray-900">{totalClaims.toLocaleString()}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-600">Total Received</h3>
          <p className="text-2xl font-bold text-green-600">{formatCurrency(totalReceived)}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-600">Avg Collection Rate</h3>
          <p className="text-2xl font-bold text-blue-600">{formatPercent(avgCollectionRate)}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-600">Unique Claim Codes</h3>
          <p className="text-2xl font-bold text-gray-900">{uniqueCodes}</p>
        </div>
      </div>

      {/* Search and Table */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium text-gray-900">Claim Code Performance</h2>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <input
                type="text"
                placeholder="Search claim codes..."
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
                  { key: 'Claim Code', label: 'Claim Code' },
                  { key: 'Total Claims', label: 'Total Claims' },
                  { key: 'Avg Billed Amount', label: 'Avg Billed' },
                  { key: 'Avg Expected Payment', label: 'Avg Expected' },
                  { key: 'Avg Actual Payment', label: 'Avg Actual' },
                  { key: 'Total Received', label: 'Total Received' },
                  { key: 'Avg Adjustment', label: 'Avg Adjustment' },
                  { key: 'Avg % Collected', label: '% Collected' }
                ].map((column) => (
                  <th
                    key={column.key}
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort(column.key as keyof CodePerformanceData)}
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
                    {item['Claim Code']}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {item['Total Claims'].toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatCurrency(item['Avg Billed Amount'])}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatCurrency(item['Avg Expected Payment'])}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatCurrency(item['Avg Actual Payment'])}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-green-600">
                    {formatCurrency(item['Total Received'])}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    <span className={item['Avg Adjustment'] < 0 ? 'text-red-600' : 'text-gray-900'}>
                      {formatCurrency(item['Avg Adjustment'])}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        item['Avg % Collected'] >= 90
                          ? 'bg-green-100 text-green-800'
                          : item['Avg % Collected'] >= 70
                          ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-red-100 text-red-800'
                      }`}
                    >
                      {formatPercent(item['Avg % Collected'])}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {sortedData.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-500">No claim codes found matching your search.</p>
          </div>
        )}
      </div>
    </div>
  )
}
