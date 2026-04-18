import React, { useState, useEffect } from 'react'
import SchemaContractCard from './SchemaContractCard'

const API_BASE = 'http://localhost:8000'

export default function SchemaReview() {
  const [locked, setLocked] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch(`${API_BASE}/api/schema/sample`)
      .then(r => {
        if (!r.ok) throw new Error('Failed to fetch schema sample')
        return r.json()
      })
      .then(data => { setLocked(data); setLoading(false) })
      .catch(err => { setError(err.message); setLoading(false) })
  }, [])

  if (loading) return <div className="dashboard"><p className="loading">Loading schema...</p></div>
  if (error) return <div className="dashboard"><p className="error">Error: {error}</p></div>

  const { manifest, content_hash, locked_at } = locked

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div>
          <h2>Schema Contract</h2>
          <p className="schema-meta">
            <span className="paper-title">{manifest.paper.title}</span>
            &nbsp;·&nbsp;
            <code className="hash-badge">#{content_hash}</code>
            &nbsp;·&nbsp;
            <span className="locked-at">locked {new Date(locked_at).toLocaleTimeString()}</span>
          </p>
        </div>
      </div>

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
            <SchemaContractCard
              key={comp.id}
              component={comp}
              contracts={manifest.tensor_contracts}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
