export default function Composer({ value, onChange, onSend, onStop, streaming, disabled }) {
  function submit() {
    if (streaming || disabled || !value.trim()) return
    onSend(value)
    onChange('')
  }

  function onKeyDown(e) {
    if (e.key === 'Escape' && streaming) {
      e.preventDefault()
      onStop()
      return
    }
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      submit()
    }
  }

  const canSend = !streaming && !disabled && value.trim().length > 0

  return (
    <div className="composer">
      <textarea
        rows={1}
        value={value}
        placeholder={
          disabled
            ? 'Connecting…'
            : streaming
              ? 'Generating… press Esc or Stop to interrupt'
              : 'Describe your task… Enter to send, Shift+Enter for a new line'
        }
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKeyDown}
        disabled={disabled}
      />
      {streaming ? (
        <button
          type="button"
          className="send-btn stop"
          onClick={onStop}
          title="Stop generation (Esc)"
        >
          Stop
        </button>
      ) : (
        <button type="button" className="send-btn" onClick={submit} disabled={!canSend}>
          Generate
        </button>
      )}
    </div>
  )
}
