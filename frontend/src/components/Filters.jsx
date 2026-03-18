import { useMemo } from 'react'

function Filters({ years, customers, selectedYear, selectedCustomer, onYearChange, onCustomerChange }) {
  const visibleCustomers = useMemo(() => customers.slice(0, 200), [customers])

  return (
    <aside className="rounded-2xl border border-slate-700/60 bg-slate-900/70 p-5 shadow-lg shadow-slate-950/20">
      <h2 className="text-base font-semibold text-slate-100">Filters</h2>
      <p className="mt-1 text-sm text-slate-400">Adjust filters to update all dashboard visuals.</p>

      <div className="mt-5 space-y-4">
        <div>
          <label htmlFor="year-filter" className="mb-2 block text-xs uppercase tracking-[0.14em] text-slate-400">
            Year
          </label>
          <select
            id="year-filter"
            value={selectedYear}
            onChange={(event) => onYearChange(event.target.value)}
            className="w-full rounded-xl border border-slate-600 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-cyan-400"
          >
            <option value="all">All Years</option>
            {years.map((year) => (
              <option key={year} value={year}>
                {year}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label
            htmlFor="customer-filter"
            className="mb-2 block text-xs uppercase tracking-[0.14em] text-slate-400"
          >
            Customer
          </label>
          <input
            id="customer-filter"
            list="customer-options"
            value={selectedCustomer}
            onChange={(event) => onCustomerChange(event.target.value)}
            placeholder="All Customers"
            className="w-full rounded-xl border border-slate-600 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-cyan-400"
          />
          <datalist id="customer-options">
            {visibleCustomers.map((customer) => (
              <option key={customer} value={customer} />
            ))}
          </datalist>
        </div>
      </div>
    </aside>
  )
}

export default Filters
