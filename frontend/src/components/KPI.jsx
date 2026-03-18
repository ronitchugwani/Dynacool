function KPI({ title, value, subtitle, accent = 'text-sky-300' }) {
  return (
    <article className="group rounded-2xl border border-slate-700/60 bg-slate-900/70 p-5 shadow-lg shadow-slate-950/30 transition-all duration-300 hover:-translate-y-0.5 hover:border-sky-400/40 hover:shadow-sky-900/20">
      <p className="text-xs font-medium uppercase tracking-[0.16em] text-slate-400">{title}</p>
      <p className={`mt-2 text-3xl font-semibold leading-tight ${accent}`}>{value}</p>
      {subtitle ? <p className="mt-2 text-sm text-slate-400">{subtitle}</p> : null}
    </article>
  )
}

export default KPI
