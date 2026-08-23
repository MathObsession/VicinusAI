export default function StatusBar({ stats }) {
  const stat = (label, value) => (
    <div className={`stat${value == null ? ' stat-empty' : ''}`}>
      <span className="stat-label">{label}</span>
      <span className="stat-value mono">{value ?? '—'}</span>
    </div>
  )

  return (
    <div className="statusbar">
      {stat('tok/s', stats.tokPerSec)}
      {stat('prompt', stats.promptTokens)}
      {stat('reused', stats.cachedTokens)}
      {stat('output', stats.completionTokens)}
      {stat('time', stats.elapsedS != null ? `${stats.elapsedS}s` : null)}
    </div>
  )
}
