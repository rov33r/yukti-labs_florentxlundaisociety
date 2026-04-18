import React, { useState, useRef } from 'react'
import PipelineProgress from './PipelineProgress'
import AsteriskSpinner from './AsteriskSpinner'

const API_BASE = 'http://localhost:8000'

const ARXIV_PATTERN = /(?:arxiv\.org\/(?:abs|pdf)\/|^)([\d]{4}\.[\d]{4,5}(?:v\d+)?|[a-z\-]+\/\d{7})$/i

function parseArxivId(raw) {
  const trimmed = raw.trim()
  const m = trimmed.match(ARXIV_PATTERN)
  return m ? m[1] : trimmed
}

export default function LandingPage({ onEnter }) {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [pipelineDone, setPipelineDone] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)

  const handleSubmit = async (e) => {
    e?.preventDefault()
    const raw = input.trim()
    if (!raw || loading) return

    setLoading(true)
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
      // Small pause so the final "done" state is visible before showing result
      setTimeout(() => {
        setResult(data)
        setLoading(false)
      }, 800)
    } catch (err) {
      setError(err.message)
      setLoading(false)
      setPipelineDone(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSubmit()
  }

  const handleReset = () => {
    setResult(null)
    setError(null)
    setInput('')
    setPipelineDone(false)
    setTimeout(() => inputRef.current?.focus(), 50)
  }

  return (
    <div className="landing-page">
      {/* Nav bar */}
      <nav className="landing-nav">
        <span className="landing-nav-logo">Yukti</span>
        <button className="btn-ghost" onClick={onEnter}>
          Open Sandbox →
        </button>
      </nav>

      {/* Hero */}
      <section className="landing-hero">
        <AsteriskSpinner size={72} color="white" className="landing-logo-icon" />
        <h1 className="landing-title">Yukti</h1>
        <p className="landing-subtitle">
          Understand ML architectures through interactive exploration
        </p>

        {/* arXiv input */}
        {!loading && !result && (
          <form className="landing-input-wrap" onSubmit={handleSubmit}>
            <input
              ref={inputRef}
              className="landing-input"
              type="text"
              placeholder="arXiv ID or URL — e.g. 1706.03762"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              autoFocus
            />
            <button
              className="btn-primary landing-submit-btn"
              type="submit"
              disabled={!input.trim()}
            >
              Research paper
            </button>
          </form>
        )}

        {error && !loading && (
          <div className="landing-error">
            <p>{error}</p>
            <button className="btn-ghost" onClick={handleReset}>Try again</button>
          </div>
        )}
      </section>

      {/* Pipeline progress */}
      {loading && (
        <section className="landing-pipeline-section">
          <div className="landing-pipeline-header">
            <AsteriskSpinner size={18} color="#EEF3FA" />
            <span className="landing-pipeline-heading">Processing paper</span>
          </div>
          <PipelineProgress done={pipelineDone} />
        </section>
      )}

      {/* Result */}
      {result && (
        <section className="landing-result">
          <div className="landing-result-card">
            <div className="landing-result-meta">
              <span className="landing-result-arxiv">{result.manifest?.paper?.arxiv_id ?? result.paper?.arxiv_id}</span>
              <span className="landing-result-badge">
                {(result.manifest?.components ?? result.components ?? []).length} components extracted
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
              <button className="btn-primary" onClick={onEnter}>
                Open in Sandbox →
              </button>
              <button className="btn-ghost" onClick={handleReset}>
                Research another paper
              </button>
            </div>
          </div>
        </section>
      )}
    </div>
  )
}
