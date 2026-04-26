import React, { useState, useRef } from 'react'
import { Network, Code2, MessageCircle } from 'lucide-react'
import PipelineProgress from './PipelineProgress'
import AsteriskSpinner from './AsteriskSpinner'

const API_BASE = 'http://localhost:8000'

const ARXIV_PATTERN = /(?:arxiv\.org\/(?:abs|pdf)\/|(?:doi\.org\/[\d.]+\/(?:arxiv\.)?)|^)([\d]{4}\.[\d]{4,5}(?:v\d+)?|[a-z\-]+\/\d{7})(?:$|[^\d])/i

function parseArxivId(raw) {
  const m = raw.trim().match(ARXIV_PATTERN)
  return m ? m[1] : raw.trim()
}

const FEATURE_CARDS = [
  {
    icon: Network,
    label: 'Architecture DAG',
    desc: 'Every component in the paper, attention, FFN, norms and more, shown as a live interactive graph',
  },
  {
    icon: Code2,
    label: 'Schema-Grounded Code',
    desc: 'PyTorch generated from the locked manifest, not from the LLM\'s memory',
  },
  {
    icon: MessageCircle,
    label: 'Ask Anything',
    desc: 'Chat with an AI that only knows what\'s in this paper\'s schema',
  },
]

export default function LandingPage({ onEnter }) {
  const [input, setInput] = useState('1706.03762')
  const [phase, setPhase] = useState('idle') // idle | loading | done | error
  const [pipelineDone, setPipelineDone] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)
  const fileInputRef = useRef(null)

  const handleImport = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => {
      try {
        const data = JSON.parse(ev.target.result)
        onEnter(data)
      } catch {
        setError('Invalid manifest JSON. Could not parse the file.')
        setPhase('error')
      }
    }
    reader.readAsText(file)
    e.target.value = ''
  }

  const handleSubmit = async (e) => {
    e?.preventDefault()
    const raw = input.trim()
    if (!raw || phase === 'loading') return

    setPhase('loading')
    setError(null)
    setResult(null)
    setPipelineDone(false)

    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 240_000)

    try {
      const res = await fetch(`${API_BASE}/api/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url_or_id: parseArxivId(raw) }),
        signal: controller.signal,
      })

      clearTimeout(timeoutId)

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Ingestion failed' }))
        throw new Error(err.detail || 'Ingestion failed')
      }

      const data = await res.json()
      setPipelineDone(true)

      setTimeout(() => {
        setResult(data)
        setPhase('done')
      }, 900)

      setTimeout(() => {
        onEnter(data)
      }, 2800)
    } catch (err) {
      clearTimeout(timeoutId)
      const msg = err.name === 'AbortError'
        ? 'Request timed out (over 4 min). The LLM extractor may be overloaded. Please try again.'
        : err.message
      setError(msg)
      setPhase('error')
    }
  }

  const handleReset = () => {
    setPhase('idle')
    setResult(null)
    setError(null)
    setInput('')
    setPipelineDone(false)
    setTimeout(() => inputRef.current?.focus(), 50)
  }

  const isLoading = phase === 'loading'
  const components = result?.manifest?.components ?? result?.components ?? []

  return (
    <div className="landing-page">
      {/* Hero */}
      <section className={`landing-hero ${isLoading || phase === 'done' ? 'landing-hero--compact' : ''}`}>
        <AsteriskSpinner
          size={isLoading ? 36 : 72}
          color="white"
          className={`landing-logo-icon ${isLoading ? 'landing-logo-icon--fast' : ''}`}
        />
        <h1 className={`landing-title ${isLoading || phase === 'done' ? 'landing-title--small' : ''}`}>
          Yukti
        </h1>
        {!isLoading && phase === 'idle' && (
          <>
            <p className="landing-tagline">
              Understand any ML paper, component by component
            </p>
            <p className="landing-subtitle">
              ML papers are dense. Yukti reads the architecture for you, maps every component into an interactive diagram, and lets you ask questions in plain English. Every answer is grounded in what the paper actually says.
            </p>
          </>
        )}
      </section>

      {/* Centre stage */}
      <div className="landing-center">
        {phase === 'idle' && (
          <>
            <form className="landing-input-wrap" onSubmit={handleSubmit}>
              <input
                ref={inputRef}
                className="landing-input"
                type="text"
                placeholder="arXiv ID or URL, e.g. 1706.03762"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                autoFocus
              />
              <button className="btn-primary landing-submit-btn" type="submit" disabled={!input.trim()}>
                Research paper
              </button>
            </form>

            {/* Feature cards — show what the user gets after submitting */}
            <div className="landing-feature-cards">
              {FEATURE_CARDS.map(({ icon: Icon, label, desc }) => (
                <div key={label} className="landing-feature-card">
                  <Icon size={16} className="landing-feature-card-icon" />
                  <span className="landing-feature-card-label">{label}</span>
                  <span className="landing-feature-card-desc">{desc}</span>
                </div>
              ))}
            </div>

            <div className="landing-secondary-actions">
              <button
                className="landing-sandbox-skip"
                onClick={() => onEnter(null)}
                title="Opens a pre-loaded example (Attention Is All You Need)"
              >
                or open sandbox directly →
              </button>
              <span className="landing-divider">·</span>
              <button className="landing-sandbox-skip" onClick={() => fileInputRef.current?.click()}>
                Load saved manifest .json →
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".json,application/json"
                style={{ display: 'none' }}
                onChange={handleImport}
              />
            </div>
          </>
        )}

        {isLoading && (
          <PipelineProgress done={pipelineDone} />
        )}

        {phase === 'error' && (
          <div className="landing-error">
            <p>{error}</p>
            <button className="btn-ghost" onClick={handleReset}>Try again</button>
          </div>
        )}

        {phase === 'done' && result && (
          <div className="landing-result-card">
            <div className="landing-result-meta">
              <span className="landing-result-arxiv">
                {result.manifest?.paper?.arxiv_id ?? result.paper?.arxiv_id}
              </span>
              <span className="landing-result-badge">
                {components.length} components
              </span>
            </div>
            <h2 className="landing-result-title">
              {result.manifest?.paper?.title ?? result.paper?.title}
            </h2>
            <p className="landing-result-authors">
              {(result.manifest?.paper?.authors ?? result.paper?.authors ?? []).join(', ')}
            </p>
            <div className="landing-result-components">
              {components.map((c) => (
                <span key={c.id} className="landing-component-chip">{c.name}</span>
              ))}
            </div>
            <p className="landing-result-entering">
              Found {components.length} components. Entering schema review…
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
