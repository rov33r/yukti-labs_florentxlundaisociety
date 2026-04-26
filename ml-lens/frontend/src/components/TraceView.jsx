import React, { useState, useEffect, useCallback } from 'react'
import AsteriskSpinner from './AsteriskSpinner'

const API_BASE = 'http://localhost:8000'

function fmt(n) {
  if (!n && n !== 0) return '—'
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000)     return `${(n / 1_000).toFixed(0)}K`
  return n.toString()
}

function StepDetail({ step }) {
  if (!step) return (
    <div className="sr-detail sr-detail-empty">
      <p>Select a component to inspect its tensor shapes and math.</p>
    </div>
  )

  return (
    <div className="sr-detail">
      <div className="sr-detail-top">
        <h4 className="sr-detail-title">{step.component_name}</h4>
        <div style={{ display: 'flex', gap: 8 }}>
          {step.parameter_count > 0 && (
            <span className="sr-param-badge">{fmt(step.parameter_count)} params</span>
          )}
          {step.flops_approx > 0 && (
            <span className="sr-flops-badge">{fmt(step.flops_approx)} FLOPs</span>
          )}
        </div>
      </div>

      <div className="sr-shape-row">
        <div className="sr-shape-pill sr-shape-in">
          <span className="sr-shape-dir">IN</span>
          <code>[{step.input_symbolic?.join(', ')}]</code>
          {step.input_concrete?.length > 0 && (
            <span className="sr-shape-concrete">{step.input_concrete.join('×')}</span>
          )}
        </div>
        <span className="sr-shape-arrow">→</span>
        <div className="sr-shape-pill sr-shape-out">
          <span className="sr-shape-dir">OUT</span>
          <code>[{step.output_symbolic?.join(', ')}]</code>
          {step.output_concrete?.length > 0 && (
            <span className="sr-shape-concrete">{step.output_concrete.join('×')}</span>
          )}
        </div>
      </div>

      {step.intermediates?.length > 0 && (
        <div className="sr-intermediates">
          <div className="sr-intermediates-label">Internal tensors</div>
          <div className="sr-intermediates-flow">
            {step.intermediates.map((it, i) => (
              <div key={i} className="sr-intermediate">
                <div className="sr-int-name">{it.name}</div>
                <code className="sr-int-shape">[{it.symbolic?.join(', ')}]</code>
                <div className="sr-int-op">{it.operation}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {step.transformation && (
        <div className="sr-math-row">
          <span className="sr-math-label">MATH</span>
          <div className="sr-math-value">
            {step.transformation.split('\n').map((line, i) => (
              <div key={i}>{line}</div>
            ))}
          </div>
        </div>
      )}

      {step.key_insight && (
        <div className="sr-insight">💡 {step.key_insight}</div>
      )}
    </div>
  )
}

export default function TraceView({ manifest }) {
  const [trace, setTrace] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [activeIdx, setActiveIdx] = useState(0)

  const runTraversal = useCallback(async () => {
    if (!manifest) return
    setLoading(true)
    setError(null)
    setTrace(null)
    setActiveIdx(0)
    try {
      const res = await fetch(`${API_BASE}/api/traverse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(manifest),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Traversal failed' }))
        throw new Error(err.detail || 'Traversal failed')
      }
      setTrace(await res.json())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [manifest])

  // Auto-run when the paper changes
  useEffect(() => {
    if (manifest) runTraversal()
  }, [manifest?.paper?.arxiv_id])

  if (!manifest) return (
    <div className="trace-view-empty">
      <p>No paper loaded — ingest a paper to run traversal.</p>
    </div>
  )

  return (
    <div className="trace-view">
      <div className="trace-view-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span className="trace-view-title">Traversal Trace</span>
          {trace && (
            <span className="trace-view-meta">
              {trace.total_components} components · {fmt(trace.total_parameters)} params
            </span>
          )}
        </div>
        <button className="btn-ghost" onClick={runTraversal} disabled={loading} style={{ fontSize: 13 }}>
          {loading
            ? <><AsteriskSpinner size={13} color="#4B5E78" /> Running…</>
            : '↺ Re-run'
          }
        </button>
      </div>

      <div className="trace-view-body">
        {loading && (
          <div className="trace-view-loading">
            <AsteriskSpinner size={32} color="#0D9488" />
            <p>Running traversal agent…</p>
          </div>
        )}

        {error && !loading && (
          <div className="trace-view-error">
            <p>Traversal failed: {error}</p>
            <button className="btn-ghost" onClick={runTraversal} style={{ marginTop: 12 }}>Retry</button>
          </div>
        )}

        {trace && !loading && (
          <div className="sr-traversal-panel trace-view-panel">
            <div className="sr-steps-list">
              <div className="sr-trace-summary">
                <span>{trace.total_components} steps</span>
                <span>{fmt(trace.total_parameters)} params</span>
              </div>
              {trace.steps.map((step, i) => (
                <button
                  key={step.component_id}
                  className={`sr-step-btn ${i === activeIdx ? 'active' : ''}`}
                  onClick={() => setActiveIdx(i)}
                >
                  <span className="sr-step-order">{i + 1}</span>
                  <span className="sr-step-name">{step.component_name}</span>
                </button>
              ))}
            </div>
            <StepDetail step={trace.steps[activeIdx] ?? null} />
          </div>
        )}
      </div>
    </div>
  )
}
