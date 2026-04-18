import React, { useState, useRef, useEffect } from 'react'
import LoadingBar from './LoadingBar'
import LoadingDots from './LoadingDots'

const STUB_RESPONSES = [
  "That's a great question. The attention mechanism allows each token to weigh all other tokens — this is why the model can capture long-range dependencies that RNNs struggle with.",
  "The softmax in the attention formula normalises scores into a probability distribution, so each token's output is a weighted sum of all value vectors.",
  "Feed-forward layers apply the same transformation independently to each position — think of them as per-token MLPs that add non-linearity after attention.",
  "Layer normalisation stabilises training by re-centering activations before they pass into the next sub-layer.",
  "I'd need a bit more context to answer precisely — could you point to which component in the diagram you're referring to?",
]

function stubReply() {
  return STUB_RESPONSES[Math.floor(Math.random() * STUB_RESPONSES.length)]
}

export default function ChatPanel() {
  const [messages, setMessages] = useState([
    {
      id: 1,
      role: 'assistant',
      content: "Hi! I'm here to help you understand the model components in the sandbox. Ask me anything about how they work or why the model behaves the way it does.",
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = () => {
    const text = input.trim()
    if (!text || loading) return

    const userMsg = { id: Date.now(), role: 'user', content: text }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setLoading(true)

    // stub — will be replaced by POST /api/chat
    setTimeout(() => {
      const reply = { id: Date.now() + 1, role: 'assistant', content: stubReply() }
      setMessages((prev) => [...prev, reply])
      setLoading(false)
    }, 800)
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <aside className="chat-panel">
      <LoadingBar loading={loading} />

      <div className="chat-panel-header">
        <span className="chat-panel-title">Model Chat</span>
        <span className="badge badge-completed">Transformer</span>
      </div>

      <div className="chat-messages">
        {messages.map((msg) => (
          <div key={msg.id} className={`chat-bubble ${msg.role}`}>
            <p>{msg.content}</p>
          </div>
        ))}
        {loading && (
          <div className="chat-bubble assistant">
            <LoadingDots />
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
        <button className="btn-primary chat-send-btn" onClick={send} disabled={loading || !input.trim()}>
          Send
        </button>
      </div>
    </aside>
  )
}
