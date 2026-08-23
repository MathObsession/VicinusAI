import { useEffect, useRef } from 'react'

function renderInline(text) {
  const nodes = []
  let key = 0
  const pattern = /(\*\*[^*]+\*\*|`[^`]+`|_[^_]+_)/g
  let last = 0
  let m
  while ((m = pattern.exec(text)) !== null) {
    if (m.index > last) nodes.push(<span key={key++}>{text.slice(last, m.index)}</span>)
    const tok = m[0]
    if (tok.startsWith('**')) nodes.push(<strong key={key++}>{tok.slice(2, -2)}</strong>)
    else if (tok.startsWith('`')) nodes.push(<code key={key++}>{tok.slice(1, -1)}</code>)
    else nodes.push(<em key={key++}>{tok.slice(1, -1)}</em>)
    last = m.index + tok.length
  }
  if (last < text.length) nodes.push(<span key={key++}>{text.slice(last)}</span>)
  return nodes
}

function Markdownish({ text }) {
  const paragraphs = text.split(/\n{2,}/)
  return paragraphs.map((p, i) => {
    const lines = p.split('\n')
    return (
      <p key={i}>
        {lines.map((line, j) => (
          <span key={j}>
            {j > 0 && <br />}
            {renderInline(line)}
          </span>
        ))}
      </p>
    )
  })
}

export default function ChatWindow({ messages, streaming, userName }) {
  const endRef = useRef(null)
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages])

  if (!messages.length) {
    return (
      <div className="chat-window chat-window-empty">
        <div className="chat-empty">
          <h2>Hi, {userName}</h2>
          <p>Spark a new conversation.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="chat-window" aria-live="polite">
      {messages.map((msg, i) => {
        const isLast = i === messages.length - 1
        const pending = isLast && streaming && msg.role === 'assistant'
        return (
          <div key={i} className={`msg msg-${msg.role}`}>
            <div className="msg-head">
              <span className="msg-role">{msg.role === 'user' ? 'You' : 'Vicinus AI'}</span>
              {pending && <span className="msg-state">generating</span>}
            </div>
            <div className="msg-body">
              {msg.content ? (
                <Markdownish text={msg.content} />
              ) : (
                <span className="caret" aria-label="generating" />
              )}
              {pending && msg.content && <span className="caret" aria-label="generating" />}
            </div>
          </div>
        )
      })}
      <div ref={endRef} />
    </div>
  )
}
