import React, { useState, useRef } from 'react'
import PipelineProgress from './PipelineProgress'
import AsteriskSpinner from './AsteriskSpinner'

const API_BASE = 'http://localhost:8000'

// Matches bare arXiv IDs, arxiv.org URLs, and DOI URLs (e.g. doi.org/10.48550/arXiv.2410.05258)
const ARXIV_PATTERN = /(?:arxiv\.org\/(?:abs|pdf)\/|(?:doi\.org\/[\d.]+\/(?:arxiv\.)?)|^)([\d]{4}\.[\d]{4,5}(?:v\d+)?|[a-z\-]+\/\d{7})(?:$|[^\d])/i

function parseArxivId(raw) {
  const m = raw.trim().match(ARXIV_PATTERN)
  return m ? m[1] : raw.trim()
}

export default function LandingPage({ onEnter }) {
  const [input, setInput] = useState('1706.03762')
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

    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 240_000) // 4 min max

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

      // Show result card briefly, then auto-navigate to sandbox
      setTimeout(() => {
        setResult(data)
        setPhase('done')
      }, 900)

      setTimeout(() => {
        onEnter(data)  // pass the full manifest to App
      }, 2800)
    } catch (err) {
      clearTimeout(timeoutId)
      const msg = err.name === 'AbortError'
        ? 'Request timed out (>4 min). The LLM extractor may be overloaded — try again.'
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

  return (
    <div className="landing-page">
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
          <>
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
            <button className="landing-sandbox-skip" onClick={() => onEnter(null)}>
              or open sandbox directly →
            </button>
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
            <p className="landing-result-entering">Opening sandbox…</p>
          </div>
        )}
      </div>
    </div>
  )
}
