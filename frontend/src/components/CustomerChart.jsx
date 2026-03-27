import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

function CustomerChart({ data }) {
  if (!data.length) {
    return (
      <section className="rounded-2xl border border-slate-700/60 bg-slate-900/70 p-5 shadow-lg shadow-slate-950/20">
        <h3 className="mb-4 text-lg font-semibold text-slate-100">Top 10 Customers</h3>
        <div className="flex h-80 items-center justify-center rounded-xl border border-dashed border-slate-700 bg-slate-950/60 text-sm text-slate-400">
          No customer ranking available for the selected filters.
        </div>
      </section>
    )
  }

  return (
    <section className="rounded-2xl border border-slate-700/60 bg-slate-900/70 p-5 shadow-lg shadow-slate-950/20 transition-all duration-300 hover:border-emerald-400/40">
      <h3 className="mb-4 text-lg font-semibold text-slate-100">Top 10 Customers</h3>
      <div className="h-80 w-full">
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 45 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis
              dataKey="customer"
              stroke="#94a3b8"
              tick={{ fill: '#94a3b8', fontSize: 11 }}
              angle={-25}
              textAnchor="end"
              height={70}
            />
            <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} />
            <Tooltip
              contentStyle={{
                background: '#0f172a',
                border: '1px solid #334155',
                borderRadius: '12px',
                color: '#e2e8f0',
              }}
            />
            <Bar dataKey="revenue" fill="#34d399" radius={[8, 8, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}

export default CustomerChart
