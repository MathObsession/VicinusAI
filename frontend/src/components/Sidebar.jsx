function formatWhen(ts) {
  const s = Math.max(0, (Date.now() - ts) / 1000)
  if (s < 60) return 'now'
  if (s < 3600) return `${Math.floor(s / 60)}m`
  if (s < 86400) return `${Math.floor(s / 3600)}h`
  return `${Math.floor(s / 86400)}d`
}

export default function Sidebar({
  health,
  mode,
  stats,
  devMode,
  onToggleDevMode,
  chats,
  activeId,
  onNewChat,
  onSelectChat,
  onDeleteChat,
}) {
  const model = health?.model
  const badge =
    mode === 'live' ? 'badge badge-live' : mode === 'connecting' ? 'badge badge-wait' : 'badge badge-sim'
  const badgeText =
    mode === 'live'
      ? 'Live · TurboFieldfareServer'
      : mode === 'connecting'
        ? 'Connecting…'
        : 'Simulated'
  const mem = stats.memoryGb ?? model?.resident_memory_gb ?? 2.05
  const memPct = Math.min(100, Math.round((mem / 8) * 100))
  const sorted = [...chats].sort((a, b) => b.updatedAt - a.updatedAt)

  return (
    <aside className="sidebar">
      <div className="brand">
        <img src="/vicinusAI.png" alt="Vicinus AI logo" className="brand-logo" />
        <div>
          <h1>Vicinus AI</h1>
          <span className="brand-sub">Web Console</span>
        </div>
      </div>

      <button type="button" className="new-chat-btn" onClick={onNewChat}>
        + New chat
      </button>
      <ul className="chat-list">
        {sorted.map((c) => (
          <li key={c.id} className={c.id === activeId ? 'active' : ''}>
            <button type="button" className="chat-item-btn" onClick={() => onSelectChat(c.id)}>
              <span className="chat-title">{c.title}</span>
              <span className="chat-when">{formatWhen(c.updatedAt)}</span>
            </button>
            <button
              type="button"
              className="chat-delete"
              aria-label={`Delete ${c.title}`}
              title="Delete chat"
              onClick={() => onDeleteChat(c.id)}
            >
              ×
            </button>
          </li>
        ))}
      </ul>

      {devMode && (
        <>
          <div className={badge}>{badgeText}</div>

          {model ? (
            <section>
              <h2>Model</h2>
              <dl className="kv">
                <dt>Checkpoint</dt>
                <dd>Gemma 4 26B-A4B IT</dd>
                <dt>Params</dt>
                <dd>26B total · ~3.88B active</dd>
                <dt>Routing</dt>
                <dd>top-8 of 128 · 16-slot LFU</dd>
              </dl>
            </section>
          ) : (
            <section>
              <h2>Model</h2>
              <p className="hint" style={{ marginTop: 0 }}>
                No upstream detected. Run TurboFieldfareServer locally for real inference.
              </p>
            </section>
          )}

          {devMode && (
            <section>
              <h2>Memory</h2>
              <p className="membar-label">{memPct}% memory used</p>
            </section>
          )}
        </>
      )}

      <footer className="sidebar-footer">
        <div className="footer-links">
          <a href="https://github.com/drumih/turbo-fieldfare" target="_blank" rel="noreferrer">
            turbo-fieldfare
          </a>
          <a
            href="https://github.com/drumih/turbo-fieldfare/blob/main/docs/OPENAI_SERVER.md"
            target="_blank"
            rel="noreferrer"
          >
            docs
          </a>
        </div>
        <label className="toggle-row">
          <span>
            <span className="toggle-title">Developer mode</span>
          </span>
          <button
            type="button"
            role="switch"
            aria-checked={devMode}
            aria-label="Developer mode"
            className={`switch${devMode ? ' on' : ''}`}
            onClick={onToggleDevMode}
          >
            <span className="knob" />
          </button>
        </label>
      </footer>
    </aside>
  )
}
