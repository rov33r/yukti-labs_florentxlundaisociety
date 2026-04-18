import React, { useState, useEffect, useRef } from 'react'
import SchemaContractCard from './SchemaContractCard'
import ArchitectureFlow from './ArchitectureFlow'

const API_BASE = 'http://localhost:8000'

export default function SchemaReview() {
  const [locked, setLocked] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [trace, setTrace] = useState(null)
  const [traversing, setTraversing] = useState(false)
  const [traverseError, setTraverseError] = useState(null)
  const [activeStepIndex, setActiveStepIndex] = useState(null)
  const [view, setView] = useState('flow') // 'flow' | 'cards'

  const intervalRef = useRef(null)

  useEffect(() => {
    fetch(`${API_BASE}/api/schema/sample`)
      .then(r => { if (!r.ok) throw new Error('Failed to fetch schema sample'); return r.json() })
      .then(data => { setLocked(data); setLoading(false) })
      .catch(err => { setError(err.message); setLoading(false) })
  }, [])

  // Auto-step through trace once loaded
  useEffect(() => {
    if (!trace) return
    setActiveStepIndex(0)
    let i = 0
    intervalRef.current = setInterval(() => {
      i++
      if (i >= trace.steps.length) { clearInterval(intervalRef.current); return }
      setActiveStepIndex(i)
    }, 1200)
    return () => clearInterval(intervalRef.current)
  }, [trace])

  async function runTraversal() {
    if (!locked) return
    setTraversing(true)
    setTraverseError(null)
    setTrace(null)
    setActiveStepIndex(null)
    try {
      const res = await fetch(`${API_BASE}/api/traverse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(locked.manifest),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Traversal failed')
      }
      setTrace(await res.json())
    } catch (err) {
      setTraverseError(err.message)
    } finally {
      setTraversing(false)
    }
  }

  if (loading) return <div className="dashboard"><p className="loading">Loading schema...</p></div>
  if (error)   return <div className="dashboard"><p className="error">Error: {error}</p></div>

  const { manifest, content_hash, locked_at } = locked
  const activeStep = trace?.steps?.[activeStepIndex] ?? null

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div>
          <h2>Schema Contract</h2>
          <p className="schema-meta">
            <span className="paper-title">{manifest.paper.title}</span>
            &nbsp;·&nbsp;<code className="hash-badge">#{content_hash}</code>
            &nbsp;·&nbsp;<span className="locked-at">locked {new Date(locked_at).toLocaleTimeString()}</span>
          </p>
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <div className="view-toggle">
            <button className={`toggle-btn ${view === 'flow' ? 'active' : ''}`} onClick={() => setView('flow')}>Flow</button>
            <button className={`toggle-btn ${view === 'cards' ? 'active' : ''}`} onClick={() => setView('cards')}>Cards</button>
          </div>
          <button
            className="btn-primary"
            onClick={runTraversal}
            disabled={traversing}
          >
            {traversing ? 'Traversing…' : trace ? '↺ Re-run Traversal' : '▶ Run Traversal'}
          </button>
        </div>
      </div>

      {traverseError && <p className="error" style={{ marginBottom: 24 }}>Traversal error: {traverseError}</p>}

      {view === 'flow' ? (
        <div style={{ marginBottom: 32 }}>
          <ArchitectureFlow
            manifest={manifest}
            trace={trace}
            activeStepIndex={activeStepIndex}
            onNodeClick={id => {
              if (!trace) return
              const idx = trace.steps.findIndex(s => s.component_id === id)
              if (idx >= 0) { clearInterval(intervalRef.current); setActiveStepIndex(idx) }
            }}
          />

          {trace && (
            <div className="traversal-panel">
              <div className="traversal-steps-list">
                <div className="trace-summary">
                  <span>{trace.total_components} components</span>
                  <span>{(trace.total_parameters / 1e6).toFixed(1)}M params</span>
                </div>
                {trace.steps.map((step, i) => (
                  <button
                    key={step.component_id}
                    className={`traversal-step-btn ${i === activeStepIndex ? 'active' : ''}`}
                    onClick={() => { clearInterval(intervalRef.current); setActiveStepIndex(i) }}
                  >
                    <span className="step-order">{i + 1}</span>
                    <span className="step-name">{step.component_name}</span>
                  </button>
                ))}
              </div>

              {activeStep && (
                <div className="traversal-detail">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                    <h4 className="detail-title">{activeStep.component_name}</h4>
                    <div style={{ display: 'flex', gap: 8 }}>
                      {activeStep.parameter_count > 0 && (
                        <span className="param-badge">{(activeStep.parameter_count / 1e6).toFixed(2)}M params</span>
                      )}
                      {activeStep.flops_approx && (
                        <span className="flops-badge">{(activeStep.flops_approx / 1e6).toFixed(1)}M FLOPs</span>
                      )}
                    </div>
                  </div>

                  {/* Shape flow */}
                  <div className="shape-flow-row">
                    <div className="shape-pill in">
                      <span className="shape-dir">IN</span>
                      <code>[{activeStep.input_symbolic?.join(', ')}]</code>
                      <span className="shape-concrete">{activeStep.input_concrete?.join('×')}</span>
                    </div>
                    <span className="shape-arrow">→</span>
                    <div className="shape-pill out">
                      <span className="shape-dir">OUT</span>
                      <code>[{activeStep.output_symbolic?.join(', ')}]</code>
                      <span className="shape-concrete">{activeStep.output_concrete?.join('×')}</span>
                    </div>
                  </div>

                  {/* Intermediates */}
                  {activeStep.intermediates?.length > 0 && (
                    <div className="intermediates-section">
                      <div className="intermediates-label">Internal tensors</div>
                      <div className="intermediates-flow">
                        {activeStep.intermediates.map((it, i) => (
                          <div key={i} className="intermediate-item">
                            <div className="intermediate-name">{it.name}</div>
                            <code className="intermediate-shape">[{it.symbolic?.join(', ')}]</code>
                            <div className="intermediate-op">{it.operation}</div>
                            {it.equation && <code className="intermediate-eq">{it.equation}</code>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Math steps */}
                  <div className="detail-row">
                    <span className="detail-label">MATH</span>
                    <div className="detail-value">
                      {activeStep.transformation?.split('\n').map((line, i) => (
                        <div key={i} style={{ marginBottom: 3 }}>{line}</div>
                      ))}
                    </div>
                  </div>

                  <div className="detail-insight">💡 {activeStep.key_insight}</div>
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        <>
          <div className="schema-symbol-table">
            <h4 className="section-title">Symbol Table</h4>
            <div className="symbol-grid">
              {Object.entries(manifest.symbol_table).map(([sym, meaning]) => (
                <div key={sym} className="symbol-row">
                  <code className="symbol">{sym}</code>
                  <span className="symbol-meaning">{meaning}</span>
                </div>
              ))}
            </div>
          </div>

          {manifest.invariants.length > 0 && (
            <div className="dashboard-section">
              <h3 className="section-title">Invariants</h3>
              <div className="invariants-list">
                {manifest.invariants.map(inv => (
                  <div key={inv.id} className="invariant-row">
                    <span className={`badge badge-${inv.kind.replace(/_/g, '-')}`}>{inv.kind}</span>
                    <span className="invariant-desc">{inv.description}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="dashboard-section">
            <h3 className="section-title">Components ({manifest.components.length})</h3>
            <div className="schema-cards-grid">
              {manifest.components.map(comp => (
                <SchemaContractCard key={comp.id} component={comp} contracts={manifest.tensor_contracts} />
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
