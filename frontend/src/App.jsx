import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchHealth, streamChat } from './api.js'
import ChatWindow from './components/ChatWindow.jsx'
import Composer from './components/Composer.jsx'
import ExpertVisualizer from './components/ExpertVisualizer.jsx'
import SettingsPanel from './components/SettingsPanel.jsx'
import Sidebar from './components/Sidebar.jsx'
import StatusBar from './components/StatusBar.jsx'

const DEFAULT_SETTINGS = {
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

const EMPTY_STATS = {
  tokPerSec: null,
  promptTokens: null,
  cachedTokens: null,
  completionTokens: null,
  elapsedS: null,
  memoryGb: null,
}

const ADJECTIVES = [
  'swift', 'curious', 'bright', 'calm', 'bold', 'early',
  'quiet', 'amber', 'clever', 'gentle', 'northern', 'little',
]
const BIRDS = [
  'fieldfare', 'heron', 'wren', 'finch', 'thrush',
  'lapwing', 'pipit', 'tern', 'harrier', 'dotterel',
]

function loadOrCreateUsername() {
  try {
    const saved = localStorage.getItem('tfw_username')
    if (saved) return saved
  } catch {
    // ignore
  }
  const name = `${ADJECTIVES[Math.floor(Math.random() * ADJECTIVES.length)]}-${
    BIRDS[Math.floor(Math.random() * BIRDS.length)]
  }`
  try {
    localStorage.setItem('tfw_username', name)
  } catch {
    // ignore
  }
  return name
}

const uid = () =>
  globalThis.crypto?.randomUUID
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`

function freshChat() {
  return { id: uid(), title: 'New chat', messages: [], updatedAt: Date.now() }
}

const LEGACY_WELCOMES = [
  'Local Gemma 4 model served by TurboFieldfare. Type a task below and press Enter.',
  'Welcome to the TurboFieldfare web console. This app proxies a local TurboFieldfareServer (Gemma 4 26B-A4B IT streamed from SSD in ~2 GB of RAM). If no server is detected on 127.0.0.1:8080, it falls back to a built-in simulator so you can still explore the chat UI and expert-streaming telemetry. Ask me how TurboFieldfare works.',
]

function loadStoredChats() {
  try {
    const arr = JSON.parse(localStorage.getItem('tfw_chats') || 'null')
    if (Array.isArray(arr)) {
      return arr
        .filter((c) => c && typeof c.id === 'string' && Array.isArray(c.messages))
        .map((c) => ({
          ...c,
          messages: c.messages.filter(
            (m) => !(m.role === 'assistant' && LEGACY_WELCOMES.includes(m.content)),
          ),
        }))
    }
  } catch {
    // corrupted storage falls through to a fresh chat
  }
  return []
}

function initialChatState() {
  let chats = loadStoredChats()
  let activeId = null
  try {
    activeId = localStorage.getItem('tfw_active_chat')
  } catch {
    // ignore
  }
  if (!chats.some((c) => c.id === activeId)) {
    if (!chats.length) chats = [freshChat()]
    activeId = chats[0].id
  }
  return { chats, activeId }
}

function deriveTitle(messages) {
  const firstUser = messages.find((m) => m.role === 'user')
  if (!firstUser) return 'New chat'
  const t = firstUser.content.trim().replace(/\s+/g, ' ')
  return t.length > 44 ? `${t.slice(0, 44)}…` : t
}

export default function App() {
  const [devMode, setDevMode] = useState(
    () => localStorage.getItem('tfw_dev_mode') === '1',
  )
  const [health, setHealth] = useState(null)
  const [chats, setChats] = useState(() => initialChatState().chats)
  const [activeId, setActiveId] = useState(() => initialChatState().activeId)
  const activeChat = chats.find((c) => c.id === activeId)
  const messages = activeChat?.messages ?? []
  const [streaming, setStreaming] = useState(false)
  const [draft, setDraft] = useState('')
  const [settings, setSettings] = useState(DEFAULT_SETTINGS)
  const [stats, setStats] = useState(EMPTY_STATS)
  const [telemetry, setTelemetry] = useState(null)
  const [error, setError] = useState(null)
  const [userName] = useState(loadOrCreateUsername)
  const abortRef = useRef(null)

  useEffect(() => {
    localStorage.setItem('tfw_dev_mode', devMode ? '1' : '0')
  }, [devMode])

  useEffect(() => {
    try {
      localStorage.setItem('tfw_chats', JSON.stringify(chats.slice(0, 40)))
      localStorage.setItem('tfw_active_chat', activeId)
    } catch {
      // storage full; keep the session working in memory
    }
  }, [chats, activeId])

  function patchChat(id, fn) {
    setChats((prev) => prev.map((c) => (c.id === id ? fn(c) : c)))
  }

  const refreshHealth = useCallback(() => {
    fetchHealth()
      .then(setHealth)
      .catch(() => setHealth({ mode: 'unreachable' }))
  }, [])

  useEffect(() => {
    refreshHealth()
    const t = setInterval(refreshHealth, 10000)
    return () => clearInterval(t)
  }, [refreshHealth])

  const send = useCallback(
    async (text) => {
      const trimmed = text.trim()
      if (!trimmed || streaming) return
      const chatId = activeId
      const history = [
        ...messages,
        { role: 'user', content: trimmed },
      ]
      patchChat(chatId, (c) => ({
        ...c,
        title: deriveTitle(history),
        updatedAt: Date.now(),
        messages: [...history, { role: 'assistant', content: '' }],
      }))
      setDraft('')
      setStreaming(true)
      setError(null)
      setStats(EMPTY_STATS)
      setTelemetry(null)

      const controller = new AbortController()
      abortRef.current = controller
      let acc = ''
      const startedAt = performance.now()
      const replaceLast = (c, msg) => ({
        ...c,
        updatedAt: Date.now(),
        messages: [...c.messages.slice(0, -1), msg],
      })

      try {
        await streamChat(
          {
            messages: history,
            options: settings,
            signal: controller.signal,
          },
          {
            onStart: (evt) => {
              if (evt.prompt_tokens != null) {
                setStats((s) => ({
                  ...s,
                  promptTokens: evt.prompt_tokens,
                  cachedTokens: evt.cached_tokens ?? 0,
                }))
              }
            },
            onToken: (piece) => {
              acc += piece
              patchChat(chatId, (c) => replaceLast(c, { role: 'assistant', content: acc }))
            },
            onTelemetry: (t) => {
              setTelemetry(t)
              setStats((s) => ({
                ...s,
                tokPerSec: t.tok_per_sec,
                memoryGb: t.memory_gb,
              }))
            },
            onUsage: (usage) => {
              setStats((s) => ({
                ...s,
                promptTokens: usage.prompt_tokens,
                completionTokens: usage.completion_tokens,
                cachedTokens: usage.cached_tokens,
              }))
            },
            onError: (text) => setError(text),
            onDone: (evt) => {
              setStats((s) => ({
                ...s,
                elapsedS:
                  evt.elapsed_s ??
                  Math.round((performance.now() - startedAt) / 100) / 10,
              }))
            },
          },
        )
      } catch (e) {
        if (e.name !== 'AbortError') setError(String(e.message || e))
        patchChat(chatId, (c) => {
          const last = c.messages[c.messages.length - 1]
          if (last?.role === 'assistant' && !last.content) {
            return replaceLast(c, {
              role: 'assistant',
              content: '_Generation stopped._',
            })
          }
          return c
        })
      } finally {
        setStreaming(false)
        abortRef.current = null
      }
    },
    [messages, settings, streaming, activeId],
  )

  const stop = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  const newChat = useCallback(() => {
    stop()
    const current = chats.find((c) => c.id === activeId)
    if (current && current.messages.length === 0) {
      patchChat(current.id, (c) => ({ ...c, title: 'New chat' }))
      return
    }
    const chat = freshChat()
    setChats((prev) => [chat, ...prev])
    setActiveId(chat.id)
    setDraft('')
  }, [chats, activeId, stop])

  const selectChat = useCallback(
    (id) => {
      if (id === activeId) return
      stop()
      setActiveId(id)
      setDraft('')
    },
    [activeId, stop],
  )

  const deleteChat = useCallback(
    (id) => {
      const next = chats.filter((c) => c.id !== id)
      const ensured = next.length ? next : [freshChat()]
      setChats(ensured)
      if (id === activeId) {
        stop()
        setActiveId(ensured[0].id)
        setDraft('')
      }
    },
    [chats, activeId, stop],
  )

  const mode = health?.mode === 'live' ? 'live' : health ? health.mode : 'connecting'

  return (
    <div className={`app-shell${devMode ? '' : ' no-dev'}`}>
      <Sidebar
        health={health}
        mode={mode}
        stats={stats}
        devMode={devMode}
        onToggleDevMode={() => setDevMode((v) => !v)}
        chats={chats}
        activeId={activeId}
        onNewChat={newChat}
        onSelectChat={selectChat}
        onDeleteChat={deleteChat}
      />
      <main className="main-col">
        <ChatWindow messages={messages} streaming={streaming} userName={userName} />
        {error && <div className="error-strip">{error}</div>}
        {devMode && <StatusBar stats={stats} />}
        <Composer
          value={draft}
          onChange={setDraft}
          onSend={send}
          onStop={stop}
          streaming={streaming}
          disabled={mode === 'connecting'}
        />
      </main>
      {devMode && (
        <aside className="right-col">
          <SettingsPanel
            settings={settings}
            onChange={setSettings}
            disabled={streaming}
            mode={mode}
          />
          <ExpertVisualizer telemetry={telemetry} active={streaming} mode={mode} />
        </aside>
      )}
    </div>
  )
}
