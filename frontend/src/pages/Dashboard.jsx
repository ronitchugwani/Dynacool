import { useEffect, useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { fetchDashboardData, fetchFilterOptions } from '../api/client'
import CategoryChart from '../components/CategoryChart'
import CustomerChart from '../components/CustomerChart'
import Filters from '../components/Filters'
import GSTChart from '../components/GSTChart'
import KPI from '../components/KPI'
import ProductChart from '../components/ProductChart'
import RevenueChart from '../components/RevenueChart'

const EMPTY_DASHBOARD = {
  kpis: {},
  monthlySales: [],
  topCustomers: [],
  gst: [],
  topProducts: [],
  categorySales: [],
}

const EMPTY_FILTER_OPTIONS = {
  years: [],
  customers: [],
  products: [],
}

function LoadingState() {
  return (
    <div className="flex h-60 flex-col items-center justify-center rounded-2xl border border-slate-700/60 bg-slate-900/70">
      <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-600 border-t-cyan-400" />
      <p className="mt-4 text-sm text-slate-300">Loading analytics data...</p>
    </div>
  )
}

function ErrorState({ message }) {
  return (
    <div className="rounded-2xl border border-rose-500/40 bg-rose-950/30 p-5">
      <h2 className="text-lg font-semibold text-rose-200">Unable to load dashboard</h2>
      <p className="mt-2 text-sm text-rose-200/90">{message}</p>
      <button
        type="button"
        onClick={() => window.location.reload()}
        className="mt-4 rounded-lg border border-rose-300/40 px-4 py-2 text-sm font-medium text-rose-100 transition hover:bg-rose-400/10"
      >
        Retry
      </button>
    </div>
  )
}

function EmptyDashboardState() {
  return (
    <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-900/60 p-6 text-center">
      <h2 className="text-lg font-semibold text-slate-100">No data for the selected filters</h2>
      <p className="mt-2 text-sm text-slate-400">
        Try broadening the year, customer, or product filters to bring records back into view.
      </p>
    </div>
  )
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

function ScopeBadge({ label, value }) {
  if (!value || value === 'all') {
    return null
  }

  return (
    <span className="rounded-full border border-cyan-400/30 bg-cyan-400/10 px-3 py-1 text-xs text-cyan-100">
      {label}: {value}
    </span>
  )
}

function Dashboard() {
  const [dashboardData, setDashboardData] = useState(EMPTY_DASHBOARD)
  const [filterOptions, setFilterOptions] = useState(EMPTY_FILTER_OPTIONS)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedYear, setSelectedYear] = useState('all')
  const [selectedCustomer, setSelectedCustomer] = useState('all')
  const [selectedProduct, setSelectedProduct] = useState('all')

  useEffect(() => {
    let cancelled = false

    async function loadDashboard() {
      setLoading(true)
      setError('')

      try {
        const filters = {
          year: selectedYear,
          customer: selectedCustomer,
          product: selectedProduct,
        }

        const [data, options] = await Promise.all([
          fetchDashboardData(filters),
          fetchFilterOptions(filters),
        ])

        if (!cancelled) {
          setDashboardData(data)
          setFilterOptions(options)
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
  }, [selectedYear, selectedCustomer, selectedProduct])

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

  const topProducts = useMemo(
    () => normalizeArray(dashboardData.topProducts, ['data', 'results', 'items']).slice(0, 10),
    [dashboardData.topProducts],
  )

  const categorySales = useMemo(
    () => normalizeArray(dashboardData.categorySales, ['data', 'results', 'items']),
    [dashboardData.categorySales],
  )

  const yearOptions = useMemo(() => {
    const fromFilters = normalizeArray(filterOptions.years).map((year) => String(year))
    const fromKpis = normalizeArray(dashboardData.kpis?.years).map((year) => String(year))
    return [...new Set([...fromFilters, ...fromKpis])].sort((a, b) => Number(a) - Number(b))
  }, [dashboardData.kpis, filterOptions.years])

  const customerOptions = useMemo(() => {
    const fromFilters = normalizeArray(filterOptions.customers)
    const fromKpis = normalizeArray(dashboardData.kpis?.customers)
    return [...new Set([...fromFilters, ...fromKpis])].sort((a, b) => a.localeCompare(b))
  }, [dashboardData.kpis, filterOptions.customers])

  const productOptions = useMemo(() => {
    const fromFilters = normalizeArray(filterOptions.products)
    const fromKpis = normalizeArray(dashboardData.kpis?.products)
    return [...new Set([...fromFilters, ...fromKpis])].sort((a, b) => a.localeCompare(b))
  }, [dashboardData.kpis, filterOptions.products])

  useEffect(() => {
    if (selectedYear !== 'all' && !yearOptions.includes(selectedYear)) {
      setSelectedYear('all')
    }
  }, [selectedYear, yearOptions])

  useEffect(() => {
    if (selectedCustomer !== 'all' && !customerOptions.includes(selectedCustomer)) {
      setSelectedCustomer('all')
    }
  }, [selectedCustomer, customerOptions])

  useEffect(() => {
    if (selectedProduct !== 'all' && !productOptions.includes(selectedProduct)) {
      setSelectedProduct('all')
    }
  }, [selectedProduct, productOptions])

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
      return Object.entries(dashboardData.gst).map(([name, value]) => ({
        name,
        value: Number(value || 0),
      }))
    }

    return gstBreakdown.map((entry) => ({
      name: entry.name || entry.component || entry.label || 'GST',
      value: Number(entry.value || entry.amount || 0),
    }))
  }, [dashboardData.gst, gstBreakdown])

  const productSeries = useMemo(
    () =>
      topProducts.map((entry) => ({
        product: entry['Item Name'] || entry.item_name || entry.product || entry.name || 'Unknown Product',
        revenue: Number(entry['Total Value'] || entry.total_value || entry.revenue || entry.value || 0),
      })),
    [topProducts],
  )

  const categorySeries = useMemo(
    () =>
      categorySales.map((entry) => ({
        name: entry.Category || entry.category || entry.name || 'Uncategorized',
        value: Number(entry['Total Value'] || entry.total_value || entry.revenue || entry.value || 0),
      })),
    [categorySales],
  )

  const revenueHistogram = useMemo(
    () => buildHistogram(revenueSeries.map((entry) => entry.revenue)),
    [revenueSeries],
  )

  const kpiSource = dashboardData.kpis || {}
  const totalRevenue = Number(
    kpiSource.total_revenue ??
      kpiSource.revenue ??
      revenueSeries.reduce((accumulator, entry) => accumulator + entry.revenue, 0),
  )
  const totalTransactions = Number(kpiSource.total_transactions ?? kpiSource.transactions ?? 0)
  const averageTransaction = Number(
    kpiSource.average_transaction_value ??
      kpiSource.avg_transaction_value ??
      (totalTransactions > 0 ? totalRevenue / totalTransactions : 0),
  )

  const hasVisualData =
    revenueSeries.length > 0 ||
    customerSeries.length > 0 ||
    gstSeries.length > 0 ||
    productSeries.length > 0 ||
    categorySeries.length > 0

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-[1400px] px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-8">
          <p className="text-xs uppercase tracking-[0.3em] text-cyan-300/90">Business Intelligence Suite</p>
          <h1 className="mt-2 text-3xl font-semibold leading-tight text-slate-50 sm:text-4xl">
            Dynacool Analytics Dashboard
          </h1>
          <p className="mt-3 max-w-2xl text-sm text-slate-400">
            Interactive revenue, customer, GST, and product insights with live backend filtering.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <ScopeBadge label="Year" value={selectedYear} />
            <ScopeBadge label="Customer" value={selectedCustomer} />
            <ScopeBadge label="Product" value={selectedProduct} />
          </div>
        </header>

        <div className="grid gap-6 lg:grid-cols-[300px_1fr]">
          <Filters
            years={yearOptions}
            customers={customerOptions}
            products={productOptions}
            selectedYear={selectedYear}
            selectedCustomer={selectedCustomer}
            selectedProduct={selectedProduct}
            onYearChange={setSelectedYear}
            onCustomerChange={setSelectedCustomer}
            onProductChange={setSelectedProduct}
            onReset={() => {
              setSelectedYear('all')
              setSelectedCustomer('all')
              setSelectedProduct('all')
            }}
          />

          <main className="space-y-6">
            {loading ? <LoadingState /> : null}
            {!loading && error ? <ErrorState message={error} /> : null}

            {!loading && !error ? (
              <>
                <section className="grid gap-4 md:grid-cols-3">
                  <KPI
                    title="Total Revenue"
                    value={toCurrency(totalRevenue)}
                    subtitle="Across selected filters"
                    accent="text-cyan-300"
                  />
                  <KPI
                    title="Total Transactions"
                    value={toInteger(totalTransactions)}
                    subtitle="Count of invoices/records"
                    accent="text-emerald-300"
                  />
                  <KPI
                    title="Average Transaction Value"
                    value={toCurrency(averageTransaction)}
                    subtitle="Revenue per transaction"
                    accent="text-amber-300"
                  />
                </section>

                {!hasVisualData && totalRevenue === 0 && totalTransactions === 0 ? <EmptyDashboardState /> : null}

                <section className="grid gap-6 xl:grid-cols-2">
                  <RevenueChart data={revenueSeries} />
                  <CustomerChart data={customerSeries} />
                </section>

                <section className="grid gap-6 xl:grid-cols-2">
                  <GSTChart data={gstSeries} />

                  <section className="rounded-2xl border border-slate-700/60 bg-slate-900/70 p-5 shadow-lg shadow-slate-950/20 transition-all duration-300 hover:border-fuchsia-400/40">
                    <h3 className="mb-4 text-lg font-semibold text-slate-100">Revenue Distribution</h3>
                    {revenueHistogram.length ? (
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
                    ) : (
                      <div className="flex h-80 items-center justify-center rounded-xl border border-dashed border-slate-700 bg-slate-950/60 text-sm text-slate-400">
                        No revenue distribution available for the selected filters.
                      </div>
                    )}
                  </section>
                </section>

                <section className="grid gap-6 xl:grid-cols-2">
                  <ProductChart data={productSeries} />
                  <CategoryChart data={categorySeries} />
                </section>
              </>
            ) : null}
          </main>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
