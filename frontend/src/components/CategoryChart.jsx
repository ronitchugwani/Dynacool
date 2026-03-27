import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

const COLORS = ['#60a5fa', '#22d3ee', '#34d399', '#f59e0b', '#f97316', '#fb7185', '#a78bfa']

function CategoryChart({ data }) {
  if (!data.length) {
    return (
      <section className="rounded-2xl border border-slate-700/60 bg-slate-900/70 p-5 shadow-lg shadow-slate-950/20">
        <h3 className="mb-4 text-lg font-semibold text-slate-100">Category Distribution</h3>
        <div className="flex h-80 items-center justify-center rounded-xl border border-dashed border-slate-700 bg-slate-950/60 text-sm text-slate-400">
          No category distribution available for the selected filters.
        </div>
      </section>
    )
  }

  return (
    <section className="rounded-2xl border border-slate-700/60 bg-slate-900/70 p-5 shadow-lg shadow-slate-950/20 transition-all duration-300 hover:border-indigo-400/40">
      <h3 className="mb-4 text-lg font-semibold text-slate-100">Category Distribution</h3>
      <div className="h-80 w-full">
        <ResponsiveContainer>
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={110} label>
              {data.map((entry, index) => (
                <Cell key={`${entry.name}-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value) => [`INR ${Number(value || 0).toLocaleString('en-IN')}`, 'Revenue']}
              contentStyle={{
                background: '#0f172a',
                border: '1px solid #334155',
                borderRadius: '12px',
                color: '#e2e8f0',
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}

export default CategoryChart
