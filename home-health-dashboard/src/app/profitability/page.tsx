'use client'

import { useEffect, useState } from 'react'
import { ArrowUpIcon, ArrowDownIcon, Search, Download, AlertTriangle, DollarSign, TrendingUp, FileSpreadsheet } from 'lucide-react'

interface OverallMetrics {
  total_revenue: number
  total_costs: number
  matched_costs: number
  unmatched_costs: number
  overhead_costs: number
  gross_profit: number
  profit_margin: number
  total_claims: number
  unique_patients: number
  unique_physicians: number
}

interface PhysicianData {
  physician: string
  revenue: number
  billed: number
  direct_costs: number
  profit: number
  margin: number
  patients: number
  claims: number
  has_matched_costs: boolean
}

interface UnmatchedPatient {
  patient_name: string
  employee: string
  amount: number
  date: string
}

interface OverheadCost {
  employee: string
  amount: number
}

interface ProfitabilityData {
  overall: OverallMetrics
  by_physician: PhysicianData[]
  unmatched_patients: UnmatchedPatient[]
  overhead: OverheadCost[]
  generated_at: string
}

export default function ProfitabilityPage() {
  const [data, setData] = useState<ProfitabilityData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sortField, setSortField] = useState<keyof PhysicianData>('revenue')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')
  const [searchTerm, setSearchTerm] = useState('')
  const [activeTab, setActiveTab] = useState<'physicians' | 'unmatched' | 'overhead'>('physicians')
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const { apiFetch } = await import('@/lib/api')
        const response = await apiFetch('/profitability/analysis')
        if (!response.ok) throw new Error('Failed to fetch profitability data')
        const profitabilityData = await response.json()
        setData(profitabilityData)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  const handleSort = (field: keyof PhysicianData) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
  }

  const handleExport = async () => {
    setExporting(true)
    try {
      const { apiFetch } = await import('@/lib/api')
      const response = await apiFetch('/profitability/export')
      if (!response.ok) throw new Error('Export failed')

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `Profitability_Analysis_${new Date().toISOString().split('T')[0]}.xlsx`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      a.remove()
    } catch (err) {
      alert('Failed to export: ' + (err instanceof Error ? err.message : 'Unknown error'))
    } finally {
      setExporting(false)
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
          <div className="grid grid-cols-5 gap-4 mb-6">
            {[...Array(5)].map((_, i) => (
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
          <h3 className="text-red-800 font-medium">Error Loading Profitability Data</h3>
          <p className="text-red-600 text-sm mt-1">{error || 'No data available'}</p>
        </div>
      </div>
    )
  }

  const { overall, by_physician, unmatched_patients, overhead } = data

  const filteredPhysicians = by_physician.filter(item =>
    item.physician.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const sortedPhysicians = [...filteredPhysicians].sort((a, b) => {
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

  const unmatchedWithAmount = unmatched_patients.filter(p => p.amount > 0)
  const unmatchedNoAmount = unmatched_patients.filter(p => p.amount === 0)

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8 flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Profitability Analysis</h1>
          <p className="text-gray-600 mt-2">
            Overall and physician-level profitability from Claims and Employee Costs
          </p>
        </div>
        <button
          onClick={handleExport}
          disabled={exporting}
          className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg font-medium transition-colors disabled:opacity-50"
        >
          {exporting ? (
            <>
              <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
              Exporting...
            </>
          ) : (
            <>
              <Download className="h-4 w-4" />
              Export to Excel
            </>
          )}
        </button>
      </div>

      {/* Overall Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-600">Total Revenue</h3>
            <DollarSign className="h-5 w-5 text-green-500" />
          </div>
          <p className="text-2xl font-bold text-green-600 mt-2">{formatCurrency(overall.total_revenue)}</p>
          <p className="text-xs text-gray-500 mt-1">{overall.total_claims} claims</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-600">Total Costs</h3>
            <FileSpreadsheet className="h-5 w-5 text-red-500" />
          </div>
          <p className="text-2xl font-bold text-red-600 mt-2">{formatCurrency(overall.total_costs)}</p>
          <p className="text-xs text-gray-500 mt-1">
            Matched: {formatCurrency(overall.matched_costs)}
          </p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-600">Gross Profit</h3>
            <TrendingUp className="h-5 w-5 text-blue-500" />
          </div>
          <p className="text-2xl font-bold text-blue-600 mt-2">{formatCurrency(overall.gross_profit)}</p>
          <p className="text-xs text-gray-500 mt-1">Revenue - Costs</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-600">Profit Margin</h3>
            <TrendingUp className="h-5 w-5 text-purple-500" />
          </div>
          <p className="text-2xl font-bold text-purple-600 mt-2">{overall.profit_margin}%</p>
          <p className="text-xs text-gray-500 mt-1">{overall.unique_physicians} physicians</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6 border-l-4 border-yellow-400">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-600">Unallocated Costs</h3>
            <AlertTriangle className="h-5 w-5 text-yellow-500" />
          </div>
          <p className="text-2xl font-bold text-yellow-600 mt-2">
            {formatCurrency(overall.unmatched_costs + overall.overhead_costs)}
          </p>
          <p className="text-xs text-gray-500 mt-1">See inconsistencies below</p>
        </div>
      </div>

      {/* Cost Breakdown Bar */}
      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <h3 className="text-sm font-medium text-gray-700 mb-3">Cost Breakdown</h3>
        <div className="flex h-8 rounded-lg overflow-hidden">
          <div
            className="bg-green-500 flex items-center justify-center text-white text-xs font-medium"
            style={{ width: `${(overall.matched_costs / overall.total_costs) * 100}%` }}
          >
            Matched ({((overall.matched_costs / overall.total_costs) * 100).toFixed(0)}%)
          </div>
          <div
            className="bg-yellow-500 flex items-center justify-center text-white text-xs font-medium"
            style={{ width: `${(overall.unmatched_costs / overall.total_costs) * 100}%` }}
          >
            Unmatched
          </div>
          <div
            className="bg-gray-400 flex items-center justify-center text-white text-xs font-medium"
            style={{ width: `${(overall.overhead_costs / overall.total_costs) * 100}%` }}
          >
            Overhead ({((overall.overhead_costs / overall.total_costs) * 100).toFixed(0)}%)
          </div>
        </div>
        <div className="flex justify-between mt-2 text-xs text-gray-600">
          <span>Matched to Physicians: {formatCurrency(overall.matched_costs)}</span>
          <span>Unmatched Patients: {formatCurrency(overall.unmatched_costs)}</span>
          <span>Overhead/Admin: {formatCurrency(overall.overhead_costs)}</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            <button
              onClick={() => setActiveTab('physicians')}
              className={`px-6 py-4 text-sm font-medium border-b-2 ${
                activeTab === 'physicians'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              By Physician ({by_physician.length})
            </button>
            <button
              onClick={() => setActiveTab('unmatched')}
              className={`px-6 py-4 text-sm font-medium border-b-2 flex items-center gap-2 ${
                activeTab === 'unmatched'
                  ? 'border-yellow-500 text-yellow-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <AlertTriangle className="h-4 w-4" />
              Unmatched Patients ({unmatchedWithAmount.length})
            </button>
            <button
              onClick={() => setActiveTab('overhead')}
              className={`px-6 py-4 text-sm font-medium border-b-2 ${
                activeTab === 'overhead'
                  ? 'border-gray-500 text-gray-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Overhead Costs ({overhead.length})
            </button>
          </nav>
        </div>

        {/* Physicians Tab */}
        {activeTab === 'physicians' && (
          <>
            <div className="p-4 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <p className="text-sm text-gray-600">
                  Direct costs only - margins shown are before overhead allocation
                </p>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                  <input
                    type="text"
                    placeholder="Search physicians..."
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
                      { key: 'physician', label: 'Physician' },
                      { key: 'revenue', label: 'Revenue' },
                      { key: 'direct_costs', label: 'Direct Costs' },
                      { key: 'profit', label: 'Profit' },
                      { key: 'margin', label: 'Margin' },
                      { key: 'patients', label: 'Patients' },
                      { key: 'claims', label: 'Claims' }
                    ].map((column) => (
                      <th
                        key={column.key}
                        className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                        onClick={() => handleSort(column.key as keyof PhysicianData)}
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
                  {sortedPhysicians.map((item, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {item.physician}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-green-600 font-medium">
                        {formatCurrency(item.revenue)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        {item.direct_costs > 0 ? (
                          <span className="text-red-600">{formatCurrency(item.direct_costs)}</span>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-blue-600">
                        {formatCurrency(item.profit)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <span className={`px-2 py-1 rounded ${
                          item.has_matched_costs
                            ? item.margin >= 50 ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                            : 'bg-gray-100 text-gray-500'
                        }`}>
                          {item.margin.toFixed(1)}%
                          {!item.has_matched_costs && '*'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {item.patients}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {item.claims}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="bg-gray-50 px-6 py-3 border-t border-gray-200">
              <p className="text-sm text-gray-600">
                * Margin shown as 100% indicates no matched costs found for this physician&apos;s patients
              </p>
            </div>
          </>
        )}

        {/* Unmatched Patients Tab */}
        {activeTab === 'unmatched' && (
          <>
            <div className="p-4 border-b border-gray-200 bg-yellow-50">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-yellow-600 mt-0.5" />
                <div>
                  <h3 className="font-medium text-yellow-800">Data Inconsistencies</h3>
                  <p className="text-sm text-yellow-700 mt-1">
                    These patient names in employee_costs.xlsx could not be matched to patients in Claim List.csv.
                    Fix these names to improve physician-level profitability accuracy.
                  </p>
                </div>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Patient Name (in employee_costs)
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Employee
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                      Amount
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Date
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {unmatchedWithAmount.map((item, index) => (
                    <tr key={index} className="hover:bg-yellow-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {item.patient_name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                        {item.employee}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-red-600 font-medium text-right">
                        {formatCurrencyDetailed(item.amount)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {item.date || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {unmatchedNoAmount.length > 0 && (
              <>
                <div className="px-6 py-3 bg-gray-100 border-t border-gray-200">
                  <p className="text-sm font-medium text-gray-700">
                    Additional unmatched entries (no amount):
                  </p>
                </div>
                <div className="px-6 py-4 bg-gray-50">
                  <div className="flex flex-wrap gap-2">
                    {unmatchedNoAmount.slice(0, 30).map((item, index) => (
                      <span
                        key={index}
                        className="px-2 py-1 bg-white border border-gray-200 rounded text-xs text-gray-600"
                      >
                        {item.patient_name}
                      </span>
                    ))}
                    {unmatchedNoAmount.length > 30 && (
                      <span className="px-2 py-1 text-xs text-gray-500">
                        +{unmatchedNoAmount.length - 30} more
                      </span>
                    )}
                  </div>
                </div>
              </>
            )}

            <div className="bg-yellow-50 px-6 py-4 border-t border-yellow-200">
              <p className="text-sm text-yellow-800">
                <strong>Total unmatched costs: {formatCurrencyDetailed(overall.unmatched_costs)}</strong>
                <span className="ml-2 text-yellow-600">
                  ({((overall.unmatched_costs / overall.total_costs) * 100).toFixed(1)}% of total costs)
                </span>
              </p>
            </div>
          </>
        )}

        {/* Overhead Tab */}
        {activeTab === 'overhead' && (
          <>
            <div className="p-4 border-b border-gray-200 bg-gray-50">
              <p className="text-sm text-gray-600">
                These costs have no patient assigned - typically admin, marketing, and general overhead.
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Employee / Category
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                      Amount
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                      % of Overhead
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {overhead.map((item, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {item.employee}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700 font-medium text-right">
                        {formatCurrencyDetailed(item.amount)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-right">
                        {((item.amount / overall.overhead_costs) * 100).toFixed(1)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="bg-gray-100 px-6 py-4 border-t border-gray-200">
              <p className="text-sm text-gray-700">
                <strong>Total overhead: {formatCurrencyDetailed(overall.overhead_costs)}</strong>
                <span className="ml-2 text-gray-500">
                  ({((overall.overhead_costs / overall.total_costs) * 100).toFixed(1)}% of total costs)
                </span>
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
