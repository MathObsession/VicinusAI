import { useEffect, useRef, useState, useCallback } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import hljs from 'highlight.js/lib/core'
import 'highlight.js/styles/github.css'

import javascript from 'highlight.js/lib/languages/javascript'
import typescript from 'highlight.js/lib/languages/typescript'
import python from 'highlight.js/lib/languages/python'
import bash from 'highlight.js/lib/languages/bash'
import json from 'highlight.js/lib/languages/json'
import xml from 'highlight.js/lib/languages/xml'
import css from 'highlight.js/lib/languages/css'
import sql from 'highlight.js/lib/languages/sql'
import rust from 'highlight.js/lib/languages/rust'
import go from 'highlight.js/lib/languages/go'
import java from 'highlight.js/lib/languages/java'
import cpp from 'highlight.js/lib/languages/cpp'
import csharp from 'highlight.js/lib/languages/csharp'
import ruby from 'highlight.js/lib/languages/ruby'
import swift from 'highlight.js/lib/languages/swift'
import markdown from 'highlight.js/lib/languages/markdown'
import yaml from 'highlight.js/lib/languages/yaml'
import diff from 'highlight.js/lib/languages/diff'

hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('js', javascript)
hljs.registerLanguage('typescript', typescript)
hljs.registerLanguage('ts', typescript)
hljs.registerLanguage('python', python)
hljs.registerLanguage('py', python)
hljs.registerLanguage('bash', bash)
hljs.registerLanguage('sh', bash)
hljs.registerLanguage('shell', bash)
hljs.registerLanguage('json', json)
hljs.registerLanguage('html', xml)
hljs.registerLanguage('xml', xml)
hljs.registerLanguage('css', css)
hljs.registerLanguage('sql', sql)
hljs.registerLanguage('rust', rust)
hljs.registerLanguage('rs', rust)
hljs.registerLanguage('go', go)
hljs.registerLanguage('java', java)
hljs.registerLanguage('cpp', cpp)
hljs.registerLanguage('c', cpp)
hljs.registerLanguage('csharp', csharp)
hljs.registerLanguage('cs', csharp)
hljs.registerLanguage('ruby', ruby)
hljs.registerLanguage('rb', ruby)
hljs.registerLanguage('swift', swift)
hljs.registerLanguage('markdown', markdown)
hljs.registerLanguage('md', markdown)
hljs.registerLanguage('yaml', yaml)
hljs.registerLanguage('yml', yaml)
hljs.registerLanguage('diff', diff)

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)
  const copy = useCallback(() => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }, [text])
  return (
    <button className="code-copy-btn" onClick={copy} aria-label="Copy code">
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

function CodeBlock({ className, children, ...props }) {
  const code = String(children).replace(/\n$/, '')
  const lang = (className || '').replace('language-', '')

  const highlighted = lang && hljs.getLanguage(lang)
    ? hljs.highlight(code, { language: lang }).value
    : hljs.highlightAuto(code).value

  return (
    <div className="code-block">
      <div className="code-block-header">
        <span className="code-lang">{lang || 'code'}</span>
        <CopyButton text={code} />
      </div>
      <pre className={`hljs ${lang ? `language-${lang}` : ''}`}>
        <code
          className={className || ''}
          dangerouslySetInnerHTML={{ __html: highlighted }}
          {...props}
        />
      </pre>
    </div>
  )
}

function InlineCode({ className, children, ...props }) {
  return <code className={className} {...props}>{children}</code>
}

function isBlockCode(children, className) {
  const text = String(children)
  return text.includes('\n') || (className || '').includes('language-')
}

const components = {
  pre({ children }) {
    return <>{children}</>
  },
  code({ className, children, ...props }) {
    if (isBlockCode(children, className)) {
      return <CodeBlock className={className} {...props}>{children}</CodeBlock>
    }
    return <InlineCode className={className} {...props}>{children}</InlineCode>
  },
  a({ href, children, ...props }) {
    return <a href={href} target="_blank" rel="noopener noreferrer" {...props}>{children}</a>
  },
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
                <Markdown remarkPlugins={[remarkGfm]} components={components}>
                  {msg.content}
                </Markdown>
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
