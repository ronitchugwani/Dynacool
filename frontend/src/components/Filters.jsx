function SelectField({ id, label, value, options, onChange, emptyLabel }) {
  return (
    <div>
      <label htmlFor={id} className="mb-2 block text-xs uppercase tracking-[0.14em] text-slate-400">
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-xl border border-slate-600 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-cyan-400"
      >
        <option value="all">{emptyLabel}</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </div>
  )
}

function ActivePill({ label, value }) {
  if (!value || value === 'all') {
    return null
  }

  return (
    <span className="rounded-full border border-cyan-400/30 bg-cyan-400/10 px-3 py-1 text-xs text-cyan-100">
      {label}: {value}
    </span>
  )
}

function Filters({
  years,
  customers,
  products,
  selectedYear,
  selectedCustomer,
  selectedProduct,
  onYearChange,
  onCustomerChange,
  onProductChange,
  onReset,
}) {
  const hasActiveFilters =
    selectedYear !== 'all' || selectedCustomer !== 'all' || selectedProduct !== 'all'

  return (
    <aside className="h-fit rounded-2xl border border-slate-700/60 bg-slate-900/70 p-5 shadow-lg shadow-slate-950/20">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-slate-100">Filters</h2>
          <p className="mt-1 text-sm text-slate-400">Adjust filters to update all dashboard visuals.</p>
        </div>

        <button
          type="button"
          onClick={onReset}
          disabled={!hasActiveFilters}
          className="rounded-lg border border-slate-600 px-3 py-2 text-xs font-medium uppercase tracking-[0.12em] text-slate-200 transition hover:border-cyan-400 hover:text-cyan-100 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Reset
        </button>
      </div>

      <div className="mt-5 space-y-4">
        <SelectField
          id="year-filter"
          label="Year"
          value={selectedYear}
          options={years}
          onChange={onYearChange}
          emptyLabel="All Years"
        />

        <SelectField
          id="customer-filter"
          label="Customer"
          value={selectedCustomer}
          options={customers}
          onChange={onCustomerChange}
          emptyLabel="All Customers"
        />

        <SelectField
          id="product-filter"
          label="Product"
          value={selectedProduct}
          options={products}
          onChange={onProductChange}
          emptyLabel="All Products"
        />
      </div>

      <div className="mt-5 border-t border-slate-800 pt-4">
        <p className="text-xs uppercase tracking-[0.14em] text-slate-500">Active Scope</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <ActivePill label="Year" value={selectedYear} />
          <ActivePill label="Customer" value={selectedCustomer} />
          <ActivePill label="Product" value={selectedProduct} />
          {!hasActiveFilters ? (
            <span className="rounded-full border border-slate-700 bg-slate-950 px-3 py-1 text-xs text-slate-400">
              No filters applied
            </span>
          ) : null}
        </div>
      </div>
    </aside>
  )
}

export default Filters
