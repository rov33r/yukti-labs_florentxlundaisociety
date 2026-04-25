import React, { useState, useRef, useEffect, useCallback } from 'react'
import hljs from 'highlight.js/lib/core'
import python from 'highlight.js/lib/languages/python'
import 'highlight.js/styles/github-dark.css'
import AsteriskSpinner from './AsteriskSpinner'

hljs.registerLanguage('python', python)

const API_BASE = 'http://localhost:8000'

export default function CodeSandbox({ manifest }) {
  const [code, setCode] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [cached, setCached] = useState(false)
  const [copied, setCopied] = useState(false)
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
          <h3 className="code-view-title">PyTorch Implementation</h3>
          {code && (
            <span className={`code-view-badge ${cached ? 'badge-cached' : 'badge-grounded'}`}>
              {cached ? 'Cached' : 'Schema-grounded'}
            </span>
          )}
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
