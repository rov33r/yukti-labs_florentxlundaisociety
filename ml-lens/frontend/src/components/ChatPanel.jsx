import React, { useState, useRef, useEffect } from 'react'
import LoadingBar from './LoadingBar'
import LoadingDots from './LoadingDots'
import MarkdownMessage from './MarkdownMessage'

const API_BASE = 'http://localhost:8000'

export default function ChatPanel({ manifest = null }) {
  const paperTitle = manifest?.paper?.title ?? null
  const [messages, setMessages] = useState([
    {
      id: 1,
      role: 'assistant',
      content: paperTitle
        ? `Schema loaded for **${paperTitle}**. Ask me anything about its components, tensor shapes, invariants, or how it differs from related architectures.`
        : "Hi! I'm here to help you understand the model components in the sandbox. Load a paper to get schema-grounded answers.",
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const send = async () => {
    const text = input.trim()
    if (!text || loading) return

    const userMsg = { id: Date.now(), role: 'user', content: text }
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

  return (
    <aside className="chat-panel">
      <LoadingBar loading={loading} label="Thinking…" />

      <div className="chat-panel-header">
        <span className="chat-panel-title">Model Chat</span>
        {paperTitle && (
          <span className="badge badge-completed" title={paperTitle}>
            {paperTitle.length > 22 ? paperTitle.slice(0, 22) + '…' : paperTitle}
          </span>
        )}
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
          <div className="chat-bubble assistant">
            <LoadingDots />
          </div>
        )}
        {error && (
          <div className="chat-bubble assistant chat-bubble-error">
            <p>Something went wrong: {error}</p>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-bar">
        <textarea
          className="chat-textarea"
          rows={2}
          placeholder="Ask about model behaviour…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          disabled={loading}
        />
        <button
          className="btn-primary chat-send-btn"
          onClick={send}
          disabled={loading || !input.trim()}
        >
          Send
        </button>
      </div>
    </aside>
  )
}
