import React, { useState, useRef } from 'react'
import PipelineProgress from './PipelineProgress'
import AsteriskSpinner from './AsteriskSpinner'

const API_BASE = 'http://localhost:8000'

const ARXIV_PATTERN = /(?:arxiv\.org\/(?:abs|pdf)\/|^)([\d]{4}\.[\d]{4,5}(?:v\d+)?|[a-z\-]+\/\d{7})$/i

function parseArxivId(raw) {
  const m = raw.trim().match(ARXIV_PATTERN)
  return m ? m[1] : raw.trim()
}

export default function LandingPage({ onEnter }) {
  const [input, setInput] = useState('')
  const [phase, setPhase] = useState('idle') // idle | loading | done | error
  const [pipelineDone, setPipelineDone] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)

  const handleSubmit = async (e) => {
    e?.preventDefault()
    const raw = input.trim()
    if (!raw || phase === 'loading') return

    setPhase('loading')
    setError(null)
    setResult(null)
    setPipelineDone(false)

    try {
      const res = await fetch(`${API_BASE}/api/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url_or_id: parseArxivId(raw) }),
      })

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
    } catch (err) {
      setError(err.message)
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

  return (
    <div className="landing-page">
      {/* Nav */}
      <nav className="landing-nav">
        <span className="landing-nav-logo">Yukti</span>
        <button className="btn-ghost" onClick={onEnter}>Open Sandbox →</button>
      </nav>

      {/* Hero — collapses when loading or done */}
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
          <p className="landing-subtitle">
            Understand ML architectures through interactive exploration
          </p>
        )}
      </section>

      {/* Centre stage — input / pipeline / result */}
      <div className="landing-center">
        {phase === 'idle' && (
          <form className="landing-input-wrap" onSubmit={handleSubmit}>
            <input
              ref={inputRef}
              className="landing-input"
              type="text"
              placeholder="arXiv ID or URL — e.g. 1706.03762"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              autoFocus
            />
            <button className="btn-primary landing-submit-btn" type="submit" disabled={!input.trim()}>
              Research paper
            </button>
          </form>
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
                {(result.manifest?.components ?? result.components ?? []).length} components
              </span>
            </div>
            <h2 className="landing-result-title">
              {result.manifest?.paper?.title ?? result.paper?.title}
            </h2>
            <p className="landing-result-authors">
              {(result.manifest?.paper?.authors ?? result.paper?.authors ?? []).join(', ')}
            </p>
            <div className="landing-result-components">
              {(result.manifest?.components ?? result.components ?? []).map((c) => (
                <span key={c.id} className="landing-component-chip">{c.name}</span>
              ))}
            </div>
            <div className="landing-result-actions">
              <button className="btn-primary" onClick={onEnter}>Open in Sandbox →</button>
              <button className="btn-ghost" onClick={handleReset}>Research another</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
