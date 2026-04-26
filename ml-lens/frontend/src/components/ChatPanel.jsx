import React, { useState, useRef, useEffect } from 'react'
import { Sparkles, Send } from 'lucide-react'
import LoadingBar from './LoadingBar'
import AsteriskSpinner from './AsteriskSpinner'
import MarkdownMessage from './MarkdownMessage'

const API_BASE = 'http://localhost:8000'

function getGreeting(paperTitle) {
  if (paperTitle) {
    return `I've read the full architecture spec for **${paperTitle}**. Ask me anything: what each component does, how data flows through it, why certain design choices were made, or how to read the tensor shapes. I only know what's in this paper's schema, so my answers are grounded, not guessed.`
  }
  return "No paper loaded yet. Head back to the home screen, paste an arXiv ID, and I'll give you grounded answers about that paper's architecture. Until then, I'm just guessing."
}

function getPromptChips(manifest) {
  if (!manifest) return []
  const components = manifest.components ?? manifest.manifest?.components ?? []
  const dynamic = components
    .filter((c) => c.kind !== 'input_embedding')
    .slice(0, 2)
    .map((c) => `What does the ${c.name} do and why is it here?`)
  return [
    'Walk me through the forward pass step by step',
    'What makes this architecture unusual or novel?',
    ...dynamic,
  ]
}

export default function ChatPanel({ manifest = null }) {
  const paperTitle = manifest?.paper?.title ?? manifest?.manifest?.paper?.title ?? null
  const [messages, setMessages] = useState([
    { id: 1, role: 'assistant', content: getGreeting(paperTitle) },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const bottomRef = useRef(null)

  const showChips = !!manifest && messages.length === 1

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const send = async (text) => {
    const msg = (text ?? input).trim()
    if (!msg || loading || !manifest) return

    const userMsg = { id: Date.now(), role: 'user', content: msg }
    const nextMessages = [...messages, userMsg]

    setMessages(nextMessages)
    setInput('')
    setLoading(true)
    setError(null)

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: nextMessages
            .filter((m) => m.role === 'user' || m.role === 'assistant')
            .map(({ role, content }) => ({ role, content })),
          manifest,
        }),
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Request failed' }))
        throw new Error(err.detail || 'Request failed')
      }

      const data = await res.json()
      setMessages((prev) => [
        ...prev,
        { id: Date.now() + 1, role: 'assistant', content: data.content },
      ])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  const chips = getPromptChips(manifest)

  return (
    <aside className="chat-panel">
      <LoadingBar loading={loading} label="Thinking…" />

      <div className="chat-panel-header">
        <div className="chat-panel-title-row">
          <Sparkles size={13} color="var(--c-teal)" />
          <span className="chat-panel-title">Ask Yukti</span>
        </div>
        <p className="chat-panel-subtitle">Schema-grounded answers only. No hallucination.</p>
      </div>

      <div className="chat-messages">
        {messages.map((msg) => (
          <div key={msg.id} className={`chat-bubble ${msg.role}`}>
            {msg.role === 'assistant'
              ? <MarkdownMessage content={msg.content} />
              : <p>{msg.content}</p>
            }
          </div>
        ))}
        {loading && (
          <div className="chat-bubble assistant chat-bubble-thinking">
            <AsteriskSpinner size={14} color="#0D9488" />
            <span className="chat-thinking-label">Thinking…</span>
          </div>
        )}
        {error && (
          <div className="chat-bubble assistant chat-bubble-error">
            <p>Something went wrong: {error}</p>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {showChips && (
        <div className="chat-prompt-chips">
          <span className="chat-prompt-chip-label">Try asking</span>
          {chips.map((chip) => (
            <button
              key={chip}
              className="chat-prompt-chip"
              onClick={() => send(chip)}
            >
              {chip}
            </button>
          ))}
        </div>
      )}

      <div className="chat-input-bar">
        <textarea
          className="chat-textarea"
          rows={2}
          placeholder={manifest ? "Ask about components, shapes, invariants…" : "Load a paper to enable chat"}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          disabled={loading || !manifest}
        />
        <button
          className="btn-primary chat-send-btn"
          onClick={() => send()}
          disabled={loading || !input.trim() || !manifest}
          title="Send (Enter)"
        >
          <Send size={14} />
        </button>
      </div>
    </aside>
  )
}
