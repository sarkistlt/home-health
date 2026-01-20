'use client'

import { useEffect, useState } from 'react'
import { DollarSign, Users, TrendingUp, AlertCircle } from 'lucide-react'
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line } from 'recharts'

interface SummaryMetrics {
  total_patients: number
  total_claims: number
  total_visits: number
  total_billed: number
  total_collected: number
  total_outstanding: number
  collection_rate: number
  avg_claim_amount: number
  total_service_cost: number
  gross_profit: number
  profit_margin: number
  last_updated: string
}

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6']

export default function Dashboard() {
  const [metrics, setMetrics] = useState<SummaryMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const { apiFetch } = await import('@/lib/api')
        const response = await apiFetch('/analytics/summary')
        if (!response.ok) throw new Error('Failed to fetch data')
        const data = await response.json()
        setMetrics(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  if (loading) {
    return (
      <div className="p-8">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="bg-white p-6 rounded-lg shadow h-24"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    const isNoData = error.includes('Failed to fetch data') || error.includes('404')
    return (
      <div className="p-8">
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-6 flex items-start">
          <AlertCircle className="h-6 w-6 text-amber-600 mr-3 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-amber-800 font-medium">
              {isNoData ? 'No Analytics Data Available' : 'Error Loading Data'}
            </h3>
            <p className="text-amber-700 text-sm mt-1">{error}</p>
            {isNoData ? (
              <div className="text-amber-700 text-sm mt-3 space-y-2">
                <p>The API server is running but no analytics data has been generated yet.</p>
                <p>To generate analytics data, you need to:</p>
                <ol className="list-decimal list-inside ml-2 space-y-1">
                  <li>Place PDF files in the <code className="bg-amber-100 px-1 rounded">data/pdfs</code> directory</li>
                  <li>Run the ETL pipeline: <code className="bg-amber-100 px-1 rounded">python3 etl_pipeline.py</code></li>
                </ol>
              </div>
            ) : (
              <p className="text-amber-700 text-sm mt-2">
                Make sure the API server is running: <code className="bg-amber-100 px-1 rounded">python3 api_server.py</code>
              </p>
            )}
          </div>
        </div>
      </div>
    )
  }

  if (!metrics) return null

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount)

  const formatPercent = (percent: number) =>
    `${percent.toFixed(1)}%`

  const kpiCards = [
    {
      title: 'Total Revenue Billed',
      value: formatCurrency(metrics.total_billed),
      icon: DollarSign,
      color: 'text-green-600',
      bgColor: 'bg-green-50'
    },
    {
      title: 'Collection Rate',
      value: formatPercent(metrics.collection_rate),
      icon: TrendingUp,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50'
    },
    {
      title: 'Outstanding Balance',
      value: formatCurrency(metrics.total_outstanding),
      icon: AlertCircle,
      color: 'text-red-600',
      bgColor: 'bg-red-50'
    },
    {
      title: 'Active Patients',
      value: metrics.total_patients.toString(),
      icon: Users,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50'
    }
  ]

  // Sample chart data (would come from API in full implementation)
  const monthlyData = [
    { month: 'Jan', revenue: metrics.total_billed * 0.15, profit: metrics.gross_profit * 0.12 },
    { month: 'Feb', revenue: metrics.total_billed * 0.18, profit: metrics.gross_profit * 0.16 },
    { month: 'Mar', revenue: metrics.total_billed * 0.22, profit: metrics.gross_profit * 0.20 },
    { month: 'Apr', revenue: metrics.total_billed * 0.25, profit: metrics.gross_profit * 0.24 },
    { month: 'May', revenue: metrics.total_billed * 0.20, profit: metrics.gross_profit * 0.28 }
  ]

  const serviceData = [
    { name: 'Skilled Nursing', value: 35, color: COLORS[0] },
    { name: 'Home Health Aide', value: 25, color: COLORS[1] },
    { name: 'Physical Therapy', value: 20, color: COLORS[2] },
    { name: 'Occupational Therapy', value: 15, color: COLORS[3] },
    { name: 'Speech Therapy', value: 5, color: COLORS[4] }
  ]

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Home Health Analytics Dashboard</h1>
        <p className="text-gray-600 mt-2">
          Comprehensive view of your billing and operational performance
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {kpiCards.map((kpi, index) => (
          <div key={index} className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className={`p-3 rounded-lg ${kpi.bgColor}`}>
                <kpi.icon className={`h-6 w-6 ${kpi.color}`} />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">{kpi.title}</p>
                <p className="text-2xl font-bold text-gray-900">{kpi.value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        {/* Revenue Trend Chart */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Revenue & Profit Trends</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={monthlyData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis tickFormatter={(value) => `$${(value / 1000).toFixed(0)}K`} />
              <Tooltip formatter={(value) => formatCurrency(value as number)} />
              <Line type="monotone" dataKey="revenue" stroke="#3B82F6" strokeWidth={2} name="Revenue" />
              <Line type="monotone" dataKey="profit" stroke="#10B981" strokeWidth={2} name="Profit" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Service Mix Chart */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Service Mix Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={serviceData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {serviceData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Financial Summary</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-600">Total Claims:</span>
              <span className="font-medium">{metrics.total_claims}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Average Claim:</span>
              <span className="font-medium">{formatCurrency(metrics.avg_claim_amount)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Gross Profit:</span>
              <span className="font-medium text-green-600">{formatCurrency(metrics.gross_profit)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Profit Margin:</span>
              <span className="font-medium">{formatPercent(metrics.profit_margin)}</span>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Operational Metrics</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-600">Total Visits:</span>
              <span className="font-medium">{metrics.total_visits}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Service Costs:</span>
              <span className="font-medium">{formatCurrency(metrics.total_service_cost)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Revenue Collected:</span>
              <span className="font-medium text-green-600">{formatCurrency(metrics.total_collected)}</span>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">System Status</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-gray-600">Data Status:</span>
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                Up to Date
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Last Updated:</span>
              <span className="font-medium text-sm">
                {new Date(metrics.last_updated).toLocaleDateString()}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
