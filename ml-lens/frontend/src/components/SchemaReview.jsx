import React, { useState, useEffect, useRef } from 'react'
import { Info, Play, RotateCcw, X } from 'lucide-react'
import SchemaContractCard from './SchemaContractCard'
import ArchitectureFlow from './ArchitectureFlow'

const API_BASE = 'http://localhost:8000'

const ORIENTATION_KEY = 'yukti.schema.orientationDismissed'

const INV_TOOLTIPS = {
  shape_invariant: 'This component must preserve a specific tensor dimension throughout the computation.',
  weight_tying: 'Two different parts of the model share the same weight matrix. This is a deliberate design choice to reduce parameter count.',
  attention_pattern: 'This constrains which tokens can attend to which other tokens.',
  normalization: 'This rule governs how activations are scaled to prevent training instability.',
}

export default function SchemaReview({ locked: lockedProp = null, onContinue = null, onBack = null }) {
  const [locked, setLocked] = useState(lockedProp)
  const [loading, setLoading] = useState(!lockedProp)
  const [error, setError] = useState(null)

  const [trace, setTrace] = useState(null)
  const [traversing, setTraversing] = useState(false)
  const [traverseError, setTraverseError] = useState(null)
  const [activeStepIndex, setActiveStepIndex] = useState(null)
  const [view, setView] = useState('flow')
  const [orientationDismissed, setOrientationDismissed] = useState(
    () => !!localStorage.getItem(ORIENTATION_KEY)
  )

  const intervalRef = useRef(null)

  useEffect(() => {
    if (lockedProp) return
    fetch(`${API_BASE}/api/schema/sample`)
      .then(r => { if (!r.ok) throw new Error('Failed to fetch schema'); return r.json() })
      .then(data => { setLocked(data); setLoading(false) })
      .catch(err => { setError(err.message); setLoading(false) })
  }, [])

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

  function dismissOrientation() {
    localStorage.setItem(ORIENTATION_KEY, '1')
    setOrientationDismissed(true)
  }

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

  if (loading) return (
    <div className="schema-page">
      <nav className="schema-nav">
        {onBack && <button className="btn-ghost schema-nav-back" onClick={onBack}>← Home</button>}
        <span className="logo">Yukti</span>
      </nav>
      <div className="dashboard"><p style={{ color: '#4B5E78', padding: 32 }}>Loading schema…</p></div>
    </div>
  )

  if (error) return (
    <div className="schema-page">
      <nav className="schema-nav">
        {onBack && <button className="btn-ghost schema-nav-back" onClick={onBack}>← Home</button>}
        <span className="logo">Yukti</span>
      </nav>
      <div className="dashboard"><p style={{ color: '#DC2626', padding: 32 }}>Error: {error}</p></div>
    </div>
  )

  const { manifest, content_hash, locked_at } = locked
  const activeStep = trace?.steps?.[activeStepIndex] ?? null

  return (
    <div className="schema-page">
      {/* Sticky nav */}
      <nav className="schema-nav">
        <div className="schema-nav-left">
          {onBack && <button className="btn-ghost schema-nav-back" onClick={onBack}>← Home</button>}
          <span className="logo">Yukti</span>
        </div>
        <div className="view-toggle">
          <button className={`toggle-btn ${view === 'flow' ? 'active' : ''}`} onClick={() => setView('flow')}>Flow</button>
          <button className={`toggle-btn ${view === 'cards' ? 'active' : ''}`} onClick={() => setView('cards')}>Cards</button>
        </div>
        <div className="schema-nav-actions">
          <button
            className="btn-ghost schema-traversal-btn"
            onClick={runTraversal}
            disabled={traversing}
            title="Simulates the forward pass and shows tensor shapes at each step"
          >
            {traversing ? (
              <><RotateCcw size={13} className="spin-icon" /> Traversing…</>
            ) : trace ? (
              <><RotateCcw size={13} /> Re-run Traversal</>
            ) : (
              <><Play size={13} /> Run Traversal</>
            )}
          </button>
          {onContinue && (
            <button className="btn-primary" onClick={onContinue}>Explore in Sandbox →</button>
          )}
        </div>
      </nav>

      <div className="dashboard">
        {/* Paper header */}
        <div className="schema-paper-header">
          <div className="schema-locked-badge">Architecture Extracted</div>
          <h2 className="schema-paper-title">{manifest.paper.title}</h2>
          <p className="schema-meta">
            <code
              className="hash-badge"
              title="This hash ensures the schema hasn't changed since extraction"
            >
              #{content_hash?.slice(0, 8)}
            </code>
            &nbsp;·&nbsp;
            <span className="locked-at">locked {new Date(locked_at).toLocaleTimeString()}</span>
            &nbsp;·&nbsp;
            <span>{manifest.components.length} components · {manifest.invariants.length} invariants</span>
          </p>
        </div>

        {/* Orientation bar — shown until dismissed */}
        {!orientationDismissed && (
          <div className="schema-orientation-bar">
            <Info size={16} className="schema-orientation-icon" />
            <p className="schema-orientation-text">
              This is the <strong>Component Manifest</strong>, a locked snapshot of the paper's neural network architecture.
              Every block in the graph is a real component from the paper with its mathematical role and tensor shapes.
              Click any block to inspect it. Run the traversal to see data flow step by step.
            </p>
            <button className="schema-orientation-dismiss" onClick={dismissOrientation}>
              Got it
            </button>
          </div>
        )}

        {traverseError && (
          <p style={{ color: '#DC2626', marginBottom: 20, fontSize: 14 }}>Traversal error: {traverseError}</p>
        )}

        {view === 'flow' ? (
          <div>
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
              <div className="sr-traversal-panel">
                <div className="sr-steps-list">
                  <div className="sr-trace-summary">
                    <span>{trace.total_components} steps</span>
                    <span
                      title="Total learnable parameters in this paper's model"
                    >
                      {(trace.total_parameters / 1e6).toFixed(1)}M params
                    </span>
                  </div>
                  {trace.steps.map((step, i) => (
                    <button
                      key={step.component_id}
                      className={`sr-step-btn ${i === activeStepIndex ? 'active' : ''}`}
                      onClick={() => { clearInterval(intervalRef.current); setActiveStepIndex(i) }}
                    >
                      <span className="sr-step-order">{i + 1}</span>
                      <span className="sr-step-name">{step.component_name}</span>
                    </button>
                  ))}
                </div>

                {activeStep ? (
                  <div className="sr-detail">
                    <div className="sr-detail-top">
                      <h4 className="sr-detail-title">{activeStep.component_name}</h4>
                      <div style={{ display: 'flex', gap: 8 }}>
                        {activeStep.parameter_count > 0 && (
                          <span className="sr-param-badge">{(activeStep.parameter_count / 1e6).toFixed(2)}M params</span>
                        )}
                        {activeStep.flops_approx && (
                          <span className="sr-flops-badge">{(activeStep.flops_approx / 1e6).toFixed(1)}M FLOPs</span>
                        )}
                      </div>
                    </div>

                    <div className="sr-shape-row">
                      <div className="sr-shape-pill sr-shape-in">
                        <span className="sr-shape-dir">IN</span>
                        <code>[{activeStep.input_symbolic?.join(', ')}]</code>
                        <span className="sr-shape-concrete">{activeStep.input_concrete?.join('×')}</span>
                      </div>
                      <span className="sr-shape-arrow">→</span>
                      <div className="sr-shape-pill sr-shape-out">
                        <span className="sr-shape-dir">OUT</span>
                        <code>[{activeStep.output_symbolic?.join(', ')}]</code>
                        <span className="sr-shape-concrete">{activeStep.output_concrete?.join('×')}</span>
                      </div>
                    </div>

                    {activeStep.intermediates?.length > 0 && (
                      <div className="sr-intermediates">
                        <div className="sr-intermediates-label">Internal tensors</div>
                        <div className="sr-intermediates-flow">
                          {activeStep.intermediates.map((it, i) => (
                            <div key={i} className="sr-intermediate">
                              <div className="sr-int-name">{it.name}</div>
                              <code className="sr-int-shape">[{it.symbolic?.join(', ')}]</code>
                              <div className="sr-int-op">{it.operation}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="sr-math-row">
                      <span className="sr-math-label">MATH</span>
                      <div className="sr-math-value">
                        {activeStep.transformation?.split('\n').map((line, i) => (
                          <div key={i}>{line}</div>
                        ))}
                      </div>
                    </div>

                    {activeStep.key_insight && (
                      <div className="sr-insight">
                        <span className="sr-insight-icon">💡</span>
                        {activeStep.key_insight}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="sr-detail sr-detail-empty">
                    <p className="sr-detail-empty-title">Select any step to inspect it</p>
                    <p className="sr-detail-empty-desc">
                      Each step shows how the tensor changes shape as it passes through that component. Input shape goes in, the operation runs, output shape comes out.
                    </p>
                  </div>
                )}
              </div>
            )}

            {!trace && (
              <div className="sr-run-hint">
                Run traversal to see per-component tensor shapes, parameter counts, and architectural insights.
              </div>
            )}
          </div>
        ) : (
          <div>
            {Object.keys(manifest.symbol_table ?? {}).length > 0 && (
              <div className="sr-section">
                <h3 className="sr-section-title">Symbol Table</h3>
                <p className="sr-section-subtitle">
                  These symbols appear in the math equations throughout the paper.
                  In tensor shape notation: <strong>B</strong> = batch size, <strong>T</strong> = sequence length, <strong>D</strong> = model dimension.
                </p>
                <div className="sr-symbol-grid">
                  {Object.entries(manifest.symbol_table).map(([sym, meaning]) => (
                    <div key={sym} className="sr-symbol-row">
                      <code className="sr-symbol">{sym}</code>
                      <span className="sr-symbol-meaning">{meaning}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {manifest.invariants.length > 0 && (
              <div className="sr-section">
                <h3 className="sr-section-title">Invariants</h3>
                <div className="sr-invariants">
                  {manifest.invariants.map(inv => (
                    <div key={inv.id} className="sr-invariant-row">
                      <span
                        className="sr-inv-badge"
                        title={INV_TOOLTIPS[inv.kind] ?? ''}
                      >
                        {inv.kind.replace(/_/g, ' ')}
                      </span>
                      <span className="sr-inv-desc">{inv.description}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="sr-section">
              <h3 className="sr-section-title">Components ({manifest.components.length})</h3>
              <div className="sr-cards-grid">
                {manifest.components.map(comp => (
                  <SchemaContractCard key={comp.id} component={comp} contracts={manifest.tensor_contracts} />
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
