import React, { useState, useRef, useEffect, useCallback } from 'react'
import hljs from 'highlight.js/lib/core'
import python from 'highlight.js/lib/languages/python'
import 'highlight.js/styles/github-dark.css'
import AsteriskSpinner from './AsteriskSpinner'

hljs.registerLanguage('python', python)

const API_BASE = 'http://localhost:8000'

function EvalBadge({ results }) {
  const b = results?.results?.baseline ?? {}
  const m = results?.results?.mllens ?? {}
  const bDrift = b.drift?.drift_errors ?? '?'
  const mDrift = m.drift?.drift_errors ?? '?'
  const runnable = m.runnable?.passed
  const shapes = m.shapes?.passed

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
      <span style={{ fontSize: 11, fontWeight: 700, color: '#4B5E78', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        Eval
      </span>
      <span style={{
        fontSize: 11, padding: '2px 8px', borderRadius: 9, fontWeight: 600,
        background: runnable ? '#F0FDF4' : '#FEF2F2',
        color: runnable ? '#16A34A' : '#DC2626',
        border: `1px solid ${runnable ? '#BBF7D0' : '#FECACA'}`,
      }}>
        {runnable ? '✅' : '❌'} Runnable
      </span>
      <span style={{
        fontSize: 11, padding: '2px 8px', borderRadius: 9, fontWeight: 600,
        background: shapes ? '#F0FDF4' : '#FEF2F2',
        color: shapes ? '#16A34A' : '#DC2626',
        border: `1px solid ${shapes ? '#BBF7D0' : '#FECACA'}`,
      }}>
        {shapes ? '✅' : '❌'} Shape
      </span>
      <span
        title={`Drift errors: baseline ${bDrift} → ML Lens ${mDrift}`}
        style={{
          fontSize: 11, padding: '2px 8px', borderRadius: 9, fontWeight: 600,
          background: '#F0F9FF', color: '#0369A1', border: '1px solid #BAE6FD',
          cursor: 'help',
        }}
      >
        Drift {bDrift}→{mDrift}
      </span>
    </div>
  )
}

export default function CodeSandbox({ manifest }) {
  const [code, setCode] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [cached, setCached] = useState(false)
  const [copied, setCopied] = useState(false)
  const [evalResults, setEvalResults] = useState(null)
  const codeRef = useRef(null)

  useEffect(() => {
    if (codeRef.current && code) {
      codeRef.current.removeAttribute('data-highlighted')
      hljs.highlightElement(codeRef.current)
    }
  }, [code])

  // Reset when a new paper is loaded
  useEffect(() => {
    setCode(null)
    setError(null)
    setCached(false)
    setEvalResults(null)
    const arxivId = manifest?.paper?.arxiv_id
    if (!arxivId) return
    fetch(`${API_BASE}/api/evals/results/${arxivId}`)
      .then(r => r.ok ? r.json() : null)
      .then(data => setEvalResults(data))
      .catch(() => {})
  }, [manifest?.paper?.arxiv_id])

  const generate = useCallback(async (forceRefresh = false) => {
    if (!manifest) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/api/codegen`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ manifest, force_refresh: forceRefresh }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Generation failed' }))
        throw new Error(err.detail || 'Code generation failed')
      }
      const data = await res.json()
      setCode(data.code)
      setCached(data.cached)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [manifest])

  const copy = useCallback(() => {
    if (!code) return
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }, [code])

  return (
    <div className="code-view-container">
      <div className="code-view-header">
        <div className="code-view-header-left">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <h3 className="code-view-title">PyTorch Implementation</h3>
              {code && (
                <span className={`code-view-badge ${cached ? 'badge-cached' : 'badge-grounded'}`}>
                  {cached ? 'Cached' : 'Schema-grounded'}
                </span>
              )}
            </div>
            {code && evalResults && <EvalBadge results={evalResults} />}
          </div>
        </div>
        {code && (
          <div className="code-view-actions">
            <button className="btn-ghost code-action-btn" onClick={copy}>
              {copied ? 'Copied!' : 'Copy'}
            </button>
            <button
              className="btn-ghost code-action-btn"
              onClick={() => generate(true)}
              disabled={loading}
            >
              ↺ Regenerate
            </button>
          </div>
        )}
      </div>

      {!code && !loading && !error && (
        <div className="code-view-empty">
          <div className="code-empty-icon">🐍</div>
          <p className="code-empty-text">
            {manifest
              ? 'Generate a schema-grounded PyTorch implementation from the loaded manifest.'
              : 'Load a paper first to generate its PyTorch implementation.'}
          </p>
          <button
            className="btn-primary"
            onClick={() => generate(false)}
            disabled={!manifest}
          >
            Generate PyTorch Source
          </button>
        </div>
      )}

      {loading && (
        <div className="code-view-empty">
          <AsteriskSpinner size={28} color="#4B5E78" />
          <p className="code-gen-loading-text">Generating schema-grounded code…</p>
          <p className="code-gen-loading-sub">This may take 15–60 seconds</p>
        </div>
      )}

      {error && !loading && (
        <div className="code-view-empty">
          <p className="code-gen-error">{error}</p>
          <button className="btn-primary" onClick={() => generate(false)}>
            Retry
          </button>
        </div>
      )}

      {code && !loading && (
        <div className="code-view-scroll">
          <pre className="code-view-pre">
            <code ref={codeRef} className="language-python">{code}</code>
          </pre>
        </div>
      )}
    </div>
  )
}
