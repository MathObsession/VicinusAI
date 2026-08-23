const CONTEXTS = [4096, 8192, 16384, 32768, 65536]

const DEFAULTS = {
  temperature: 0.2,
  top_k: 64,
  top_p: 0.95,
  seed: '',
  context: 16384,
  prefill: 'on',
  rdadvise: 'bounded',
  cache_slots: 16,
  resident_layers: 0,
}

export default function SettingsPanel({ settings, onChange, disabled, mode }) {
  function set(key, value) {
    onChange({ ...settings, [key]: value })
  }

  return (
    <>
      <section className="settings">
        <h2>Sampling</h2>
        <label className="field">
          <span>Temperature</span>
          <input
            type="range"
            min="0"
            max="2"
            step="0.05"
            value={settings.temperature}
            disabled={disabled}
            onChange={(e) => set('temperature', Number(e.target.value))}
          />
          <code>{Number(settings.temperature ?? 0).toFixed(2)}</code>
        </label>
        <label className="field">
          <span>Top-K</span>
          <input
            type="number"
            min="1"
            max="128"
            value={settings.top_k}
            disabled={disabled}
            onChange={(e) => set('top_k', e.target.value === '' ? '' : Number(e.target.value))}
          />
          <span />
        </label>
        <label className="field">
          <span>Top-P</span>
          <input
            type="number"
            min="0"
            max="1"
            step="0.01"
            value={settings.top_p}
            disabled={disabled}
            onChange={(e) => set('top_p', e.target.value === '' ? '' : Number(e.target.value))}
          />
          <span />
        </label>
        <label className="field">
          <span>Seed</span>
          <input
            type="text"
            inputMode="numeric"
            placeholder="random"
            value={settings.seed}
            disabled={disabled}
            onChange={(e) => set('seed', e.target.value.replace(/[^0-9]/g, ''))}
          />
          <span />
        </label>
      </section>

      <section className="settings">
        <h2>Runtime</h2>
        <label className="field">
          <span>Context</span>
          <select
            value={settings.context}
            disabled={disabled}
            onChange={(e) => set('context', Number(e.target.value))}
          >
            {CONTEXTS.map((v) => (
              <option key={v} value={v}>
                {v / 1024}K
              </option>
            ))}
          </select>
          <span />
        </label>
        <div className="field">
          <span>Prefill</span>
          <button
            type="button"
            role="switch"
            aria-checked={settings.prefill === 'on'}
            aria-label="Chunked prefill"
            className={`switch${settings.prefill === 'on' ? ' on' : ''}`}
            disabled={disabled}
            onClick={() => set('prefill', settings.prefill === 'on' ? 'off' : 'on')}
          >
            <span className="knob" />
          </button>
          <code>{settings.prefill}</code>
        </div>
        <label className="field">
          <span>Rdadvise</span>
          <select
            value={settings.rdadvise}
            disabled={disabled}
            onChange={(e) => set('rdadvise', e.target.value)}
          >
            <option value="off">off</option>
            <option value="bounded">bounded</option>
          </select>
          <span />
        </label>
        <label className="field">
          <span>Cache slots</span>
          <input
            type="number"
            min="4"
            max="64"
            step="4"
            value={settings.cache_slots}
            disabled={disabled}
            onChange={(e) =>
              set('cache_slots', e.target.value === '' ? '' : Number(e.target.value))
            }
          />
          <span />
        </label>
        <label className="field">
          <span>Resident layers</span>
          <input
            type="number"
            min="0"
            max="30"
            value={settings.resident_layers}
            disabled={disabled}
            onChange={(e) =>
              set('resident_layers', e.target.value === '' ? '' : Number(e.target.value))
            }
          />
          <span />
        </label>
        <p className="hint">
          {mode === 'live'
            ? 'Live server flags are fixed per process — relaunch TurboFieldfareServer to apply.'
            : 'Applied live by the simulator.'}
        </p>
      </section>

      <section className="settings">
        <button
          type="button"
          className="ghost-btn"
          style={{ marginTop: 0 }}
          disabled={disabled}
          onClick={() => onChange(DEFAULTS)}
        >
          Reset defaults
        </button>
      </section>
    </>
  )
}
