'use client'

import { useEffect, useState, useMemo } from 'react'
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { Search, ChevronDown, ChevronUp, DollarSign, TrendingUp, TrendingDown, Download } from 'lucide-react'

interface ClaimRecord {
  [key: string]: string | number | undefined
  'Patient Code': string
  'Patient Name': string
  'Claim Code': string
  'SOC Date': string
  'Claim Start': string
  'Claim End': string
  'Primary Physician': string
  'Primary Insurance': string
  'Claim Type': string
  'Status': string
  'Claim Amount': number
  'Paid Amount': number
  'Adjusted Amount': number
  'Balance': number
  'Final Sent Date': string
}

interface CostRecord {
  [key: string]: string | number | undefined
  Physician: string
  Patient_Name: string
  Date: string
  Date_Paid: string
  Status: string
  Number_Of_Visits: number
  Charge_Per_Visit: number
  Total_Amount: number
  Payment_Method: string
  Notes: string
}

interface MonthlyData {
  month: string
  billed: number
  paid: number
  costs: number
  profit: number
  patients: number
  claims: number
}

export default function ExplorerPage() {
  const [claims, setClaims] = useState<ClaimRecord[]>([])
  const [costs, setCosts] = useState<CostRecord[]>([])
  const [monthlyData, setMonthlyData] = useState<MonthlyData[]>([])
  const [physicians, setPhysicians] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [activeTab, setActiveTab] = useState<'overview' | 'claims' | 'costs'>('overview')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [selectedPhysician, setSelectedPhysician] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [groupByFields, setGroupByFields] = useState<string[]>([])
  const [showGroupByMenu, setShowGroupByMenu] = useState(false)

  const groupByOptions = ['Patient Name', 'Primary Physician', 'SOC Date', 'Claim Code']

  const toggleGroupByField = (field: string) => {
    setGroupByFields(prev =>
      prev.includes(field)
        ? prev.filter(f => f !== field)
        : [...prev, field]
    )
  }

  // Sorting
  const [sortField, setSortField] = useState<string>('')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const { apiFetch } = await import('@/lib/api')

        const [claimsRes, costsRes, monthlyRes, physiciansRes] = await Promise.all([
          apiFetch('/explorer/claims'),
          apiFetch('/explorer/costs'),
          apiFetch('/explorer/monthly-summary'),
          apiFetch('/explorer/physicians')
        ])

        if (!claimsRes.ok || !costsRes.ok || !monthlyRes.ok) {
          throw new Error('Failed to fetch data')
        }

        const claimsData = await claimsRes.json()
        const costsData = await costsRes.json()
        const monthlyDataRes = await monthlyRes.json()
        const physiciansData = await physiciansRes.json()

        setClaims(claimsData.data)
        setCosts(costsData.data)
        setMonthlyData(monthlyDataRes.data)
        setPhysicians(physiciansData)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(amount || 0)

  const handleExport = async () => {
    setExporting(true)
    try {
      const { apiFetch } = await import('@/lib/api')
      const response = await apiFetch('/explorer/export')
      if (!response.ok) throw new Error('Export failed')

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `Data_Explorer_Export_${new Date().toISOString().split('T')[0]}.xlsx`
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

  // Filter claims
  const filteredClaims = useMemo(() => {
    return claims.filter(claim => {
      if (dateFrom && claim['Claim Start'] < dateFrom) return false
      if (dateTo && claim['Claim Start'] > dateTo) return false
      if (selectedPhysician && claim['Primary Physician'] !== selectedPhysician) return false
      if (searchTerm) {
        const search = searchTerm.toLowerCase()
        return (
          claim['Patient Name']?.toLowerCase().includes(search) ||
          claim['Primary Physician']?.toLowerCase().includes(search) ||
          claim['Claim Code']?.toString().includes(search)
        )
      }
      return true
    })
  }, [claims, dateFrom, dateTo, selectedPhysician, searchTerm])

  // Filter costs
  const filteredCosts = useMemo(() => {
    return costs.filter(cost => {
      if (dateFrom && cost.Date && cost.Date < dateFrom) return false
      if (dateTo && cost.Date && cost.Date > dateTo) return false
      if (searchTerm) {
        const search = searchTerm.toLowerCase()
        return (
          cost.Patient_Name?.toLowerCase().includes(search) ||
          cost.Physician?.toLowerCase().includes(search)
        )
      }
      return true
    })
  }, [costs, dateFrom, dateTo, searchTerm])

  // Filter monthly data
  const filteredMonthly = useMemo(() => {
    return monthlyData.filter(m => {
      if (dateFrom && m.month < dateFrom.slice(0, 7)) return false
      if (dateTo && m.month > dateTo.slice(0, 7)) return false
      return true
    })
  }, [monthlyData, dateFrom, dateTo])

  // Sort function
  const sortData = <T extends Record<string, unknown>>(data: T[], field: string): T[] => {
    if (!field) return data
    return [...data].sort((a, b) => {
      const aVal = a[field]
      const bVal = b[field]
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDir === 'asc' ? aVal - bVal : bVal - aVal
      }
      const aStr = String(aVal || '')
      const bStr = String(bVal || '')
      return sortDir === 'asc' ? aStr.localeCompare(bStr) : bStr.localeCompare(aStr)
    })
  }

  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDir('desc')
    }
  }

  // Summary stats
  const claimsSummary = useMemo(() => ({
    totalBilled: filteredClaims.reduce((sum, c) => sum + (c['Claim Amount'] || 0), 0),
    totalPaid: filteredClaims.reduce((sum, c) => sum + (c['Paid Amount'] || 0), 0),
    totalBalance: filteredClaims.reduce((sum, c) => sum + (c['Balance'] || 0), 0),
    count: filteredClaims.length
  }), [filteredClaims])

  const costsSummary = useMemo(() => ({
    total: filteredCosts.reduce((sum, c) => sum + (c.Total_Amount || 0), 0),
    count: filteredCosts.filter(c => c.Total_Amount > 0).length
  }), [filteredCosts])

  // Grouped claims data
  const groupedClaims = useMemo(() => {
    if (groupByFields.length === 0) return null

    const groups: Record<string, {
      key: string
      keyParts: Record<string, string>
      count: number
      totalBilled: number
      totalPaid: number
      totalBalance: number
      patients: Set<string>
      physicians: Set<string>
      firstDate: string
      lastDate: string
    }> = {}

    filteredClaims.forEach(claim => {
      // Build composite key from all selected fields
      const keyParts: Record<string, string> = {}
      groupByFields.forEach(field => {
        if (field === 'Patient Name') keyParts[field] = claim['Patient Name'] || 'Unknown'
        else if (field === 'Claim Code') keyParts[field] = String(claim['Claim Code']) || 'Unknown'
        else if (field === 'SOC Date') keyParts[field] = claim['SOC Date'] || 'Unknown'
        else if (field === 'Primary Physician') keyParts[field] = claim['Primary Physician'] || 'Unknown'
      })
      const key = groupByFields.map(f => keyParts[f]).join(' | ')

      if (!groups[key]) {
        groups[key] = {
          key,
          keyParts,
          count: 0,
          totalBilled: 0,
          totalPaid: 0,
          totalBalance: 0,
          patients: new Set(),
          physicians: new Set(),
          firstDate: claim['Claim Start'] || '',
          lastDate: claim['Claim Start'] || ''
        }
      }

      const g = groups[key]
      g.count++
      g.totalBilled += claim['Claim Amount'] || 0
      g.totalPaid += claim['Paid Amount'] || 0
      g.totalBalance += claim['Balance'] || 0
      if (claim['Patient Name']) g.patients.add(claim['Patient Name'])
      if (claim['Primary Physician']) g.physicians.add(claim['Primary Physician'])
      if (claim['Claim Start'] && claim['Claim Start'] < g.firstDate) g.firstDate = claim['Claim Start']
      if (claim['Claim Start'] && claim['Claim Start'] > g.lastDate) g.lastDate = claim['Claim Start']
    })

    return Object.values(groups)
      .map(g => ({
        ...g,
        patients: g.patients.size,
        physicians: g.physicians.size
      }))
      .sort((a, b) => b.totalPaid - a.totalPaid)
  }, [filteredClaims, groupByFields])

  // Grouped costs data
  const groupedCosts = useMemo(() => {
    if (groupByFields.length === 0) return null

    const groups: Record<string, {
      key: string
      keyParts: Record<string, string>
      count: number
      totalAmount: number
      totalVisits: number
      employees: Set<string>
      patients: Set<string>
      firstDate: string
      lastDate: string
    }> = {}

    filteredCosts.forEach(cost => {
      // Build composite key from all selected fields
      const keyParts: Record<string, string> = {}
      groupByFields.forEach(field => {
        if (field === 'Patient Name') keyParts[field] = cost.Patient_Name || 'No Patient'
        else if (field === 'Primary Physician') keyParts[field] = cost.Physician || 'Unknown'
        else if (field === 'SOC Date' || field === 'Claim Code') keyParts[field] = cost.Date || 'No Date'
      })
      const key = groupByFields.map(f => keyParts[f]).join(' | ')

      if (!groups[key]) {
        groups[key] = {
          key,
          keyParts,
          count: 0,
          totalAmount: 0,
          totalVisits: 0,
          employees: new Set(),
          patients: new Set(),
          firstDate: cost.Date || '',
          lastDate: cost.Date || ''
        }
      }

      const g = groups[key]
      g.count++
      g.totalAmount += cost.Total_Amount || 0
      g.totalVisits += cost.Number_Of_Visits || 0
      if (cost.Physician) g.employees.add(cost.Physician)
      if (cost.Patient_Name) g.patients.add(cost.Patient_Name)
      if (cost.Date && cost.Date < g.firstDate) g.firstDate = cost.Date
      if (cost.Date && cost.Date > g.lastDate) g.lastDate = cost.Date
    })

    return Object.values(groups)
      .map(g => ({
        ...g,
        employees: g.employees.size,
        patients: g.patients.size
      }))
      .sort((a, b) => b.totalAmount - a.totalAmount)
  }, [filteredCosts, groupByFields])

  // Costs breakdown by employee for pie chart
  const costsBreakdown = useMemo(() => {
    const byEmployee: Record<string, number> = {}
    filteredCosts.forEach(cost => {
      const employee = cost.Physician || 'Unknown'
      byEmployee[employee] = (byEmployee[employee] || 0) + (cost.Total_Amount || 0)
    })

    return Object.entries(byEmployee)
      .map(([name, value]) => ({ name, value }))
      .filter(item => item.value > 0)
      .sort((a, b) => b.value - a.value)
      .slice(0, 10) // Top 10
  }, [filteredCosts])

  const PIE_COLORS = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#14b8a6', '#3b82f6', '#8b5cf6', '#ec4899', '#6b7280', '#78716c']

  if (loading) {
    return (
      <div className="p-8">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/3 mb-6"></div>
          <div className="h-64 bg-gray-200 rounded mb-6"></div>
          <div className="h-96 bg-gray-200 rounded"></div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h3 className="text-red-800 font-medium">Error Loading Data</h3>
          <p className="text-red-600 text-sm mt-1">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-6 flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Data Explorer</h1>
          <p className="text-gray-600 mt-2">
            Explore revenue and cost data with filters and charts
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

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">From Date</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="border border-gray-300 rounded px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">To Date</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="border border-gray-300 rounded px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Physician</label>
            <select
              value={selectedPhysician}
              onChange={(e) => setSelectedPhysician(e.target.value)}
              className="border border-gray-300 rounded px-3 py-2 text-sm min-w-[200px]"
            >
              <option value="">All Physicians</option>
              {physicians.map(p => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </div>
          <div className="relative">
            <label className="block text-xs font-medium text-gray-600 mb-1">Group By</label>
            <button
              type="button"
              onClick={() => setShowGroupByMenu(!showGroupByMenu)}
              className="border border-gray-300 rounded px-3 py-2 text-sm min-w-[180px] bg-white text-left flex items-center justify-between"
            >
              <span className={groupByFields.length === 0 ? 'text-gray-500' : 'text-gray-900'}>
                {groupByFields.length === 0 ? 'No Grouping' : groupByFields.join(' + ')}
              </span>
              <ChevronDown className="h-4 w-4 text-gray-400" />
            </button>
            {showGroupByMenu && (
              <div className="absolute z-10 mt-1 w-56 bg-white border border-gray-200 rounded-lg shadow-lg">
                <div className="p-2">
                  {groupByOptions.map(option => (
                    <label
                      key={option}
                      className="flex items-center gap-2 px-3 py-2 hover:bg-gray-50 rounded cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={groupByFields.includes(option)}
                        onChange={() => toggleGroupByField(option)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="text-sm text-gray-700">{option}</span>
                    </label>
                  ))}
                </div>
                <div className="border-t border-gray-200 p-2">
                  <button
                    onClick={() => {
                      setGroupByFields([])
                      setShowGroupByMenu(false)
                    }}
                    className="w-full text-left px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 rounded"
                  >
                    Clear Grouping
                  </button>
                </div>
              </div>
            )}
          </div>
          <div className="flex-1">
            <label className="block text-xs font-medium text-gray-600 mb-1">Search</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <input
                type="text"
                placeholder="Search patients, physicians..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="border border-gray-300 rounded pl-10 pr-3 py-2 text-sm w-full max-w-md"
              />
            </div>
          </div>
          <button
            onClick={() => {
              setDateFrom('')
              setDateTo('')
              setSelectedPhysician('')
              setSearchTerm('')
              setGroupByFields([])
            }}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 border border-gray-300 rounded"
          >
            Clear Filters
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Revenue (Paid)</span>
            <DollarSign className="h-4 w-4 text-green-500" />
          </div>
          <p className="text-2xl font-bold text-green-600">{formatCurrency(claimsSummary.totalPaid)}</p>
          <p className="text-xs text-gray-500">{claimsSummary.count} claims</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Billed Amount</span>
            <TrendingUp className="h-4 w-4 text-blue-500" />
          </div>
          <p className="text-2xl font-bold text-blue-600">{formatCurrency(claimsSummary.totalBilled)}</p>
          <p className="text-xs text-gray-500">Outstanding: {formatCurrency(claimsSummary.totalBalance)}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Total Costs</span>
            <TrendingDown className="h-4 w-4 text-red-500" />
          </div>
          <p className="text-2xl font-bold text-red-600">{formatCurrency(costsSummary.total)}</p>
          <p className="text-xs text-gray-500">{costsSummary.count} payments</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Net Profit</span>
            <DollarSign className="h-4 w-4 text-purple-500" />
          </div>
          <p className="text-2xl font-bold text-purple-600">
            {formatCurrency(claimsSummary.totalPaid - costsSummary.total)}
          </p>
          <p className="text-xs text-gray-500">
            {((claimsSummary.totalPaid - costsSummary.total) / claimsSummary.totalPaid * 100).toFixed(1)}% margin
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            <button
              onClick={() => setActiveTab('overview')}
              className={`px-6 py-4 text-sm font-medium border-b-2 ${
                activeTab === 'overview'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Monthly Overview
            </button>
            <button
              onClick={() => setActiveTab('claims')}
              className={`px-6 py-4 text-sm font-medium border-b-2 ${
                activeTab === 'claims'
                  ? 'border-green-500 text-green-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Claims ({filteredClaims.length})
            </button>
            <button
              onClick={() => setActiveTab('costs')}
              className={`px-6 py-4 text-sm font-medium border-b-2 ${
                activeTab === 'costs'
                  ? 'border-red-500 text-red-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Costs ({filteredCosts.length})
            </button>
          </nav>
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Monthly Revenue vs Costs</h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={filteredMonthly}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                  <YAxis tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                  <Tooltip
                    formatter={(value) => formatCurrency(Number(value))}
                    labelFormatter={(label) => `Month: ${label}`}
                  />
                  <Legend />
                  <Bar dataKey="paid" name="Revenue (Paid)" fill="#10b981" />
                  <Bar dataKey="costs" name="Costs" fill="#ef4444" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <h3 className="text-lg font-medium text-gray-900 mb-4 mt-8">Profit Trend</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={filteredMonthly}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                  <YAxis tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                  <Tooltip formatter={(value) => formatCurrency(Number(value))} />
                  <Legend />
                  <Line type="monotone" dataKey="profit" name="Profit" stroke="#8b5cf6" strokeWidth={2} />
                  <Line type="monotone" dataKey="billed" name="Billed" stroke="#3b82f6" strokeWidth={1} strokeDasharray="5 5" />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <h3 className="text-lg font-medium text-gray-900 mb-4 mt-8">Claims & Patients</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={filteredMonthly}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="claims" name="Claims" fill="#6366f1" />
                  <Bar dataKey="patients" name="Unique Patients" fill="#f59e0b" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Claims Tab */}
        {activeTab === 'claims' && (
          <div className="overflow-x-auto">
            {groupByFields.length > 0 && groupedClaims ? (
              <>
                <div className="p-3 bg-blue-50 border-b border-blue-200 text-sm text-blue-800">
                  Grouped by <strong>{groupByFields.join(' + ')}</strong> - {groupedClaims.length} groups
                </div>
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{groupByFields.join(' + ')}</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Claims</th>
                      {!groupByFields.includes('Patient Name') && <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Patients</th>}
                      {!groupByFields.includes('Primary Physician') && <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Physicians</th>}
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total Billed</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total Paid</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Balance</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date Range</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {groupedClaims.slice(0, 100).map((group, i) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm font-medium text-gray-900">{group.key}</td>
                        <td className="px-4 py-3 text-sm text-gray-900">{group.count}</td>
                        {!groupByFields.includes('Patient Name') && <td className="px-4 py-3 text-sm text-gray-600">{group.patients}</td>}
                        {!groupByFields.includes('Primary Physician') && <td className="px-4 py-3 text-sm text-gray-600">{group.physicians}</td>}
                        <td className="px-4 py-3 text-sm text-blue-600 font-medium text-right">{formatCurrency(group.totalBilled)}</td>
                        <td className="px-4 py-3 text-sm text-green-600 font-medium text-right">{formatCurrency(group.totalPaid)}</td>
                        <td className="px-4 py-3 text-sm text-red-600 font-medium text-right">{formatCurrency(group.totalBalance)}</td>
                        <td className="px-4 py-3 text-sm text-gray-500">{group.firstDate} to {group.lastDate}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {groupedClaims.length > 100 && (
                  <div className="p-4 bg-gray-50 text-sm text-gray-600">
                    Showing 100 of {groupedClaims.length} groups.
                  </div>
                )}
              </>
            ) : (
              <>
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      {['Claim Start', 'Patient Name', 'Primary Physician', 'Claim Amount', 'Paid Amount', 'Balance', 'Status', 'Final Sent Date'].map(col => (
                        <th
                          key={col}
                          onClick={() => handleSort(col)}
                          className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                        >
                          <div className="flex items-center gap-1">
                            {col}
                            {sortField === col && (
                              sortDir === 'asc' ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />
                            )}
                          </div>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {sortData(filteredClaims, sortField).slice(0, 100).map((claim, i) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm text-gray-900">{claim['Claim Start']}</td>
                        <td className="px-4 py-3 text-sm font-medium text-gray-900">{claim['Patient Name']}</td>
                        <td className="px-4 py-3 text-sm text-gray-600">{claim['Primary Physician']}</td>
                        <td className="px-4 py-3 text-sm text-blue-600 font-medium">{formatCurrency(claim['Claim Amount'])}</td>
                        <td className="px-4 py-3 text-sm text-green-600 font-medium">{formatCurrency(claim['Paid Amount'])}</td>
                        <td className="px-4 py-3 text-sm text-red-600 font-medium">{formatCurrency(claim['Balance'])}</td>
                        <td className="px-4 py-3 text-sm">
                          <span className={`px-2 py-1 rounded text-xs ${
                            claim['Status'] === 'Sent' ? 'bg-green-100 text-green-800' :
                            claim['Status'] === 'Hold' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {claim['Status']}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500">{claim['Final Sent Date']}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {filteredClaims.length > 100 && (
                  <div className="p-4 bg-gray-50 text-sm text-gray-600">
                    Showing 100 of {filteredClaims.length} claims. Use filters to narrow results.
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* Costs Tab */}
        {activeTab === 'costs' && (
          <div>
            {/* Pie Chart - always show */}
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Costs by Employee (Top 10)</h3>
              <div className="flex flex-col lg:flex-row gap-6">
                <div className="h-64 w-full lg:w-1/2">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={costsBreakdown}
                        cx="50%"
                        cy="50%"
                        innerRadius={40}
                        outerRadius={80}
                        paddingAngle={2}
                        dataKey="value"
                      >
                        {costsBreakdown.map((_, index) => (
                          <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value) => formatCurrency(Number(value))} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex-1">
                  <div className="grid grid-cols-2 gap-2">
                    {costsBreakdown.map((item, index) => (
                      <div key={item.name} className="flex items-center gap-2 text-sm">
                        <div
                          className="w-3 h-3 rounded-full flex-shrink-0"
                          style={{ backgroundColor: PIE_COLORS[index % PIE_COLORS.length] }}
                        />
                        <span className="truncate text-gray-700">{item.name}</span>
                        <span className="text-gray-500 ml-auto">{formatCurrency(item.value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="overflow-x-auto">
            {groupByFields.length > 0 && groupedCosts ? (
              <>
                <div className="p-3 bg-red-50 border-b border-red-200 text-sm text-red-800">
                  Grouped by <strong>{groupByFields.map(f => f === 'Primary Physician' ? 'Employee' : f).join(' + ')}</strong> - {groupedCosts.length} groups
                </div>
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        {groupByFields.map(f => f === 'Primary Physician' ? 'Employee' : f).join(' + ')}
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Records</th>
                      {!groupByFields.includes('Patient Name') && <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Patients</th>}
                      {!groupByFields.includes('Primary Physician') && <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Employees</th>}
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total Visits</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total Amount</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date Range</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {groupedCosts.slice(0, 100).map((group, i) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm font-medium text-gray-900">{group.key}</td>
                        <td className="px-4 py-3 text-sm text-gray-900">{group.count}</td>
                        {!groupByFields.includes('Patient Name') && <td className="px-4 py-3 text-sm text-gray-600">{group.patients}</td>}
                        {!groupByFields.includes('Primary Physician') && <td className="px-4 py-3 text-sm text-gray-600">{group.employees}</td>}
                        <td className="px-4 py-3 text-sm text-gray-900 text-right">{group.totalVisits || '-'}</td>
                        <td className="px-4 py-3 text-sm text-red-600 font-medium text-right">{formatCurrency(group.totalAmount)}</td>
                        <td className="px-4 py-3 text-sm text-gray-500">{group.firstDate || '-'} to {group.lastDate || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {groupedCosts.length > 100 && (
                  <div className="p-4 bg-gray-50 text-sm text-gray-600">
                    Showing 100 of {groupedCosts.length} groups.
                  </div>
                )}
              </>
            ) : (
              <>
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      {['Date', 'Physician', 'Patient_Name', 'Number_Of_Visits', 'Charge_Per_Visit', 'Total_Amount', 'Date_Paid', 'Payment_Method'].map(col => (
                        <th
                          key={col}
                          onClick={() => handleSort(col)}
                          className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                        >
                          <div className="flex items-center gap-1">
                            {col.replace(/_/g, ' ')}
                            {sortField === col && (
                              sortDir === 'asc' ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />
                            )}
                          </div>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {sortData(filteredCosts, sortField).slice(0, 100).map((cost, i) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm text-gray-900">{cost.Date || '-'}</td>
                        <td className="px-4 py-3 text-sm font-medium text-gray-900">{cost.Physician}</td>
                        <td className="px-4 py-3 text-sm text-gray-600">{cost.Patient_Name || '-'}</td>
                        <td className="px-4 py-3 text-sm text-gray-900">{cost.Number_Of_Visits || '-'}</td>
                        <td className="px-4 py-3 text-sm text-gray-900">
                          {cost.Charge_Per_Visit ? formatCurrency(cost.Charge_Per_Visit) : '-'}
                        </td>
                        <td className="px-4 py-3 text-sm text-red-600 font-medium">
                          {cost.Total_Amount ? formatCurrency(cost.Total_Amount) : '-'}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500">{cost.Date_Paid || '-'}</td>
                        <td className="px-4 py-3 text-sm text-gray-500">{cost.Payment_Method || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {filteredCosts.length > 100 && (
                  <div className="p-4 bg-gray-50 text-sm text-gray-600">
                    Showing 100 of {filteredCosts.length} cost records. Use filters to narrow results.
                  </div>
                )}
              </>
            )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
