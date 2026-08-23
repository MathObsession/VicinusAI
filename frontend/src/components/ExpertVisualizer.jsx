const STATE_CLASS = {
  idle: 'cell-idle',
  cached: 'cell-cached',
  active: 'cell-active',
}

export default function ExpertVisualizer({ telemetry, active, mode }) {
  const states = telemetry?.expert_states

  return (
    <section className="visualizer">
      <h2>Expert cache</h2>
      {states ? (
        <>
          <p className="hint">
            Layer {telemetry.layer_sample} · top-8 of 128 experts per token
          </p>
          <div className={`grid${active ? ' grid-live' : ''}`}>
            {states.map((s, i) => (
              <div key={i} className={`cell ${STATE_CLASS[s]}`} title={`expert ${i}: ${s}`} />
            ))}
          </div>
          <dl className="kv compact tele">
            <dt>Cache hit</dt>
            <dd>{(telemetry.cache_hit_rate * 100).toFixed(1)}%</dd>
            <dt>SSD reads</dt>
            <dd>{telemetry.bytes_read_mb} MB</dd>
            <dt>KV tokens</dt>
            <dd>{telemetry.kv_tokens}</dd>
          </dl>
          <p className="legend">
            <span><span className="lg lg-active" /> active</span>
            <span><span className="lg lg-cached" /> cached</span>
            <span><span className="lg lg-idle" /> on SSD</span>
          </p>
        </>
      ) : mode === 'live' ? (
        <p className="hint dim">Router telemetry is produced by the simulator only.</p>
      ) : (
        <p className="hint dim">Send a message to see expert caching in action.</p>
      )}
    </section>
  )
}
