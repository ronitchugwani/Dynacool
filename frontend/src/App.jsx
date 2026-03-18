import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { fetchDashboardData } from './api/client'
import Filters from './components/Filters'
import KPI from './components/KPI'
const RevenueChart = lazy(() => import('./components/RevenueChart'))
const CustomerChart = lazy(() => import('./components/CustomerChart'))
const GSTChart = lazy(() => import('./components/GSTChart'))

function ChartSkeleton() {
  return (
    <div className="h-80 animate-pulse rounded-2xl border border-slate-700/60 bg-slate-900/70" />
  )
}

const EMPTY_DASHBOARD = {
  kpis: {},
  monthlySales: [],
  topCustomers: [],
  gst: [],
}

function toCurrency(value) {
  const amount = Number(value || 0)
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount)
}

function toInteger(value) {
  const number = Number(value || 0)
  return new Intl.NumberFormat('en-IN').format(number)
}

function normalizeArray(payload, fallbackKeys = []) {
  if (Array.isArray(payload)) {
    return payload
  }
  for (const key of fallbackKeys) {
    if (Array.isArray(payload?.[key])) {
      return payload[key]
    }
  }
  return []
}

function buildHistogram(values, binCount = 10) {
  const series = values
    .map((value) => Number(value))
    .filter((value) => Number.isFinite(value))

  if (!series.length) {
    return []
  }

  const min = Math.min(...series)
  const max = Math.max(...series)

  if (min === max) {
    return [{ bucket: `${Math.round(min)}`, count: series.length }]
  }

  const step = (max - min) / binCount
  const bins = Array.from({ length: binCount }, (_, index) => {
    const start = min + index * step
    const end = start + step
    return { start, end, count: 0 }
  })

  for (const value of series) {
    const position = Math.min(Math.floor((value - min) / step), binCount - 1)
    bins[position].count += 1
  }

  return bins.map((bin) => ({
    bucket: `${Math.round(bin.start / 1000)}k-${Math.round(bin.end / 1000)}k`,
    count: bin.count,
  }))
}

function App() {
  const [dashboardData, setDashboardData] = useState(EMPTY_DASHBOARD)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [selectedYear, setSelectedYear] = useState('all')
  const [selectedCustomer, setSelectedCustomer] = useState('')

  useEffect(() => {
    let cancelled = false

    async function loadDashboard() {
      setLoading(true)
      setError('')

      try {
        const data = await fetchDashboardData({
          year: selectedYear,
          customer: selectedCustomer || 'all',
        })
        if (!cancelled) {
          setDashboardData(data)
        }
      } catch (apiError) {
        if (!cancelled) {
          setError(apiError?.response?.data?.detail || apiError.message || 'Failed to load dashboard data.')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    loadDashboard()

    return () => {
      cancelled = true
    }
  }, [selectedYear, selectedCustomer])

  const monthlySales = useMemo(
    () => normalizeArray(dashboardData.monthlySales, ['data', 'results', 'items']),
    [dashboardData.monthlySales],
  )
  const topCustomers = useMemo(
    () => normalizeArray(dashboardData.topCustomers, ['data', 'results', 'items']).slice(0, 10),
    [dashboardData.topCustomers],
  )
  const gstBreakdown = useMemo(
    () => normalizeArray(dashboardData.gst, ['breakdown', 'data', 'items']),
    [dashboardData.gst],
  )

  const yearOptions = useMemo(() => {
    const fromEndpoint = normalizeArray(dashboardData.kpis?.years)
      .map((year) => String(year))
      .filter((year) => /^\d{4}$/.test(year))

    const fromSeries = monthlySales
      .map((entry) => {
        const key = entry.month || entry.year_month || entry.label
        if (!key) {
          return null
        }
        const parsed = new Date(String(key))
        return Number.isNaN(parsed.getTime()) ? String(key).slice(0, 4) : String(parsed.getFullYear())
      })
      .filter((year) => typeof year === 'string' && /^\d{4}$/.test(year))

    return [...new Set([...fromEndpoint, ...fromSeries])].sort((a, b) => Number(a) - Number(b))
  }, [dashboardData.kpis, monthlySales])

  const customerOptions = useMemo(() => {
    const fromEndpoint = normalizeArray(dashboardData.kpis?.customers)
    const fromTop = topCustomers.map((entry) => entry.customer || entry.name).filter(Boolean)
    return [...new Set([...fromEndpoint, ...fromTop])].sort((a, b) => a.localeCompare(b))
  }, [dashboardData.kpis, topCustomers])

  const revenueSeries = useMemo(
    () =>
      monthlySales.map((entry) => ({
        month: entry.month || entry.year_month || entry.label || 'Unknown',
        revenue: Number(entry.revenue || entry.total_revenue || entry.value || 0),
      })),
    [monthlySales],
  )

  const customerSeries = useMemo(
    () =>
      topCustomers.map((entry) => ({
        customer: entry.customer || entry.name || 'Unknown',
        revenue: Number(entry.revenue || entry.value || entry.total || 0),
      })),
    [topCustomers],
  )

  const gstSeries = useMemo(() => {
    if (!gstBreakdown.length && dashboardData.gst && typeof dashboardData.gst === 'object') {
      return Object.entries(dashboardData.gst).map(([name, value]) => ({ name, value: Number(value || 0) }))
    }
    return gstBreakdown.map((entry) => ({
      name: entry.name || entry.component || entry.label || 'GST',
      value: Number(entry.value || entry.amount || 0),
    }))
  }, [dashboardData.gst, gstBreakdown])

  const revenueHistogram = useMemo(() => buildHistogram(revenueSeries.map((entry) => entry.revenue)), [revenueSeries])

  const kpiSource = dashboardData.kpis || {}
  const totalRevenue = Number(kpiSource.total_revenue ?? kpiSource.revenue ?? revenueSeries.reduce((acc, item) => acc + item.revenue, 0))
  const totalTransactions = Number(kpiSource.total_transactions ?? kpiSource.transactions ?? 0)
  const averageTransaction = Number(
    kpiSource.average_transaction_value ??
      kpiSource.avg_transaction_value ??
      (totalTransactions > 0 ? totalRevenue / totalTransactions : 0),
  )

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-[1400px] px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-8">
          <p className="text-xs uppercase tracking-[0.3em] text-cyan-300/90">Sales Intelligence</p>
          <h1 className="mt-2 text-3xl font-semibold leading-tight text-slate-50 sm:text-4xl">
            Business Analytics Command Center
          </h1>
          <p className="mt-3 max-w-2xl text-sm text-slate-400">
            Revenue, customer behavior, GST composition, and trend signals in one responsive operational view.
          </p>
        </header>

        <div className="grid gap-6 lg:grid-cols-[290px_1fr]">
          <Filters
            years={yearOptions}
            customers={customerOptions}
            selectedYear={selectedYear}
            selectedCustomer={selectedCustomer}
            onYearChange={setSelectedYear}
            onCustomerChange={setSelectedCustomer}
          />

          <main className="space-y-6">
            {loading ? (
              <div className="flex h-60 flex-col items-center justify-center rounded-2xl border border-slate-700/60 bg-slate-900/70">
                <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-600 border-t-cyan-400" />
                <p className="mt-4 text-sm text-slate-300">Loading analytics data...</p>
              </div>
            ) : null}

            {!loading && error ? (
              <div className="rounded-2xl border border-rose-500/40 bg-rose-950/30 p-5">
                <h2 className="text-lg font-semibold text-rose-200">Unable to load dashboard</h2>
                <p className="mt-2 text-sm text-rose-200/90">{error}</p>
                <button
                  type="button"
                  onClick={() => window.location.reload()}
                  className="mt-4 rounded-lg border border-rose-300/40 px-4 py-2 text-sm font-medium text-rose-100 transition hover:bg-rose-400/10"
                >
                  Retry
                </button>
              </div>
            ) : null}

            {!loading && !error ? (
              <>
                <section className="grid gap-4 md:grid-cols-3">
                  <KPI title="Total Revenue" value={toCurrency(totalRevenue)} subtitle="Across selected filters" accent="text-cyan-300" />
                  <KPI title="Total Transactions" value={toInteger(totalTransactions)} subtitle="Count of invoices/records" accent="text-emerald-300" />
                  <KPI title="Average Transaction Value" value={toCurrency(averageTransaction)} subtitle="Revenue per transaction" accent="text-amber-300" />
                </section>

                <Suspense fallback={<ChartSkeleton />}>
                  <section className="grid gap-6 xl:grid-cols-2">
                    <RevenueChart data={revenueSeries} />
                    <CustomerChart data={customerSeries} />
                  </section>
                </Suspense>

                <section className="grid gap-6 xl:grid-cols-2">
                  <Suspense fallback={<ChartSkeleton />}>
                    <GSTChart data={gstSeries} />
                  </Suspense>

                  <section className="rounded-2xl border border-slate-700/60 bg-slate-900/70 p-5 shadow-lg shadow-slate-950/20 transition-all duration-300 hover:border-fuchsia-400/40">
                    <h3 className="mb-4 text-lg font-semibold text-slate-100">Revenue Distribution</h3>
                    <div className="h-80 w-full">
                      <ResponsiveContainer>
                        <BarChart data={revenueHistogram} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                          <XAxis dataKey="bucket" stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                          <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                          <Tooltip
                            contentStyle={{
                              background: '#0f172a',
                              border: '1px solid #334155',
                              borderRadius: '12px',
                              color: '#e2e8f0',
                            }}
                          />
                          <Bar dataKey="count" fill="#e879f9" radius={[8, 8, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </section>
                </section>
              </>
            ) : null}
          </main>
        </div>
      </div>
    </div>
  )
}

export default App
