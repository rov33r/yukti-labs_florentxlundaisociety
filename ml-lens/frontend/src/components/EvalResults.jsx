import React, { useState, useEffect } from 'react'

const API_BASE = 'http://localhost:8000'

const PAPER_INTERPRETATIONS = {
  '2410.05258': {
    baseline: `Without the schema, the model hallucinated 3 missing components and used **GroupNorm** instead of the paper's **RMSNorm** — a fundamental architectural error from blending DiffTransformer with vanilla Transformer patterns in training data.`,
    mllens: `With the locked ComponentManifest injected, the model produced all 8 correct components, correct normalization, correct FFN variant (SwiGLU), and the differential attention scalar mechanism. Drift errors dropped from 4 to 1.`,
    note: `The ML Lens generated code had a minor RoPE shape arithmetic bug (2-line fix). The architectural structure was fully correct — the failure was implementation arithmetic, not architectural confusion.`,
  },
  '2305.13245': {
    baseline: `Without the schema, the baseline used a dimensionally incorrect \`gather()\` to expand K/V heads — the tensor index had the wrong number of dimensions, causing a runtime crash. The paper's key invariant (K/V via \`repeat_interleave\`, not gather) was missed entirely.`,
    mllens: `With the manifest injected, the model used the correct \`repeat_interleave\` expansion and produced a model that runs and returns the right output shape (B, T, vocab_size). The manifest's \`weight_tying_mqa\` invariant directly prevented the baseline's error.`,
    note: `The ML Lens generated code is intentionally compact — it consolidates sub-components into fewer classes. Drift score reflects missing sub-module keywords, not a structural error.`,
  },
}

function bucketLabel(key) {
  return key
    .split('_')
    .map(w => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

function yesno(passed) {
  if (passed === undefined || passed === null) return '—'
  return passed ? '✅' : '❌'
}

function deltaStr(bVal, mVal, isBool = false) {
  if (isBool) {
    if (mVal && !bVal) return { text: '+100%', good: true }
    if (!mVal && bVal) return { text: '−100%', good: false }
    return { text: '0%', good: null }
  }
  if (bVal === 0 && mVal === 0) return { text: '0%', good: null }
  if (bVal === 0) return { text: '+∞', good: false }
  const pct = ((bVal - mVal) / bVal) * 100
  const good = pct > 0
  const sign = pct >= 0 ? '+' : ''
  return { text: `${sign}${pct.toFixed(0)}%`, good }
}

export default function EvalResults({ onBack }) {
  const [papers, setPapers] = useState([])
  const [activePaper, setActivePaper] = useState(null)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch(`${API_BASE}/api/evals/papers`)
      .then(r => r.json())
      .then(list => {
        setPapers(list)
        if (list.length > 0) setActivePaper(list[0])
        else setLoading(false)
      })
      .catch(err => { setError(err.message); setLoading(false) })
  }, [])

  useEffect(() => {
    if (!activePaper) return
    setLoading(true)
    setError(null)
    fetch(`${API_BASE}/api/evals/results/${activePaper}`)
      .then(r => { if (!r.ok) throw new Error('Failed to fetch results'); return r.json() })
      .then(d => { setData(d); setLoading(false) })
      .catch(err => { setError(err.message); setLoading(false) })
  }, [activePaper])

  return (
    <div className="dashboard" style={{ maxWidth: 860, margin: '0 auto', padding: '40px 32px' }}>
      <div className="dashboard-header" style={{ marginBottom: 24 }}>
        <div>
          <h2 style={{ marginBottom: 4 }}>Hallucination Eval — ΔH Report</h2>
          <p className="schema-meta" style={{ color: '#4B5E78' }}>
            n=2 papers · same model, same decoding · only variable: ML Lens schema injection
          </p>
        </div>
        {onBack && <button className="btn-ghost" onClick={onBack}>← Back</button>}
      </div>

      {/* Paper tabs */}
      {papers.length > 0 && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 32 }}>
          {papers.map(pid => (
            <button
              key={pid}
              onClick={() => setActivePaper(pid)}
              style={{
                padding: '6px 16px',
                borderRadius: 6,
                border: '1px solid',
                borderColor: activePaper === pid ? '#0D9488' : '#E2E8F0',
                background: activePaper === pid ? '#F0FDF9' : '#fff',
                color: activePaper === pid ? '#0D9488' : '#4B5E78',
                fontFamily: 'Poppins, sans-serif',
                fontSize: 13,
                fontWeight: activePaper === pid ? 600 : 400,
                cursor: 'pointer',
              }}
            >
              {pid}
            </button>
          ))}
        </div>
      )}

      {loading && <p style={{ color: '#4B5E78' }}>Loading results…</p>}
      {error && <p style={{ color: '#DC2626' }}>Error: {error}</p>}
      {!loading && !error && data && <PaperReport data={data} />}
    </div>
  )
}

function PaperReport({ data }) {
  const { paper_id, paper_title, required_module_keywords, results } = data
  const b = results?.baseline ?? {}
  const m = results?.mllens ?? {}
  const interp = PAPER_INTERPRETATIONS[paper_id] ?? {}

  const bRunnable = b.runnable?.passed ?? false
  const mRunnable = m.runnable?.passed ?? false
  const bShapes = b.shapes?.passed ?? false
  const mShapes = m.shapes?.passed ?? false
  const bDrift = b.drift?.drift_errors ?? 0
  const mDrift = m.drift?.drift_errors ?? 0

  const dRunnable = deltaStr(bRunnable, mRunnable, true)
  const dShapes = deltaStr(bShapes, mShapes, true)
  const dDrift = deltaStr(bDrift, mDrift)

  const bClasses = b.drift?.classes ?? []
  const mClasses = m.drift?.classes ?? []
  const buckets = Object.keys(required_module_keywords)
  const bCovered = b.drift?.buckets_covered ?? {}
  const mCovered = m.drift?.buckets_covered ?? {}

  return (
    <>
      {/* Paper header */}
      <div style={{ marginBottom: 32 }}>
        <p className="schema-meta">
          Paper: <span className="paper-title">{paper_title}</span>
          &nbsp;·&nbsp;<code className="hash-badge">{paper_id}</code>
        </p>
      </div>

      {/* Headline metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, marginBottom: 40 }}>
        <MetricCard label="Runnable" baseline={yesno(bRunnable)} mllens={yesno(mRunnable)} delta={dRunnable} />
        <MetricCard label="Shape Correct" baseline={yesno(bShapes)} mllens={yesno(mShapes)} delta={dShapes} />
        <MetricCard
          label="Drift Errors"
          baseline={String(bDrift)}
          mllens={String(mDrift)}
          delta={dDrift}
          highlight={dDrift.good}
        />
      </div>

      {/* Bucket coverage table */}
      <div className="dashboard-section" style={{ marginBottom: 40 }}>
        <h3 className="section-title" style={{ marginBottom: 16 }}>Architecture Bucket Coverage</h3>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #E2E8F0' }}>
              <th style={{ textAlign: 'left', padding: '8px 12px', fontFamily: 'Poppins, sans-serif', color: '#4B5E78' }}>Bucket</th>
              <th style={{ textAlign: 'left', padding: '8px 12px', fontFamily: 'Poppins, sans-serif', color: '#E57373' }}>Baseline</th>
              <th style={{ textAlign: 'left', padding: '8px 12px', fontFamily: 'Poppins, sans-serif', color: '#4CAF50' }}>ML Lens</th>
            </tr>
          </thead>
          <tbody>
            {buckets.map(key => {
              const bHit = bCovered[key]
              const mHit = mCovered[key]
              return (
                <tr key={key} style={{ borderBottom: '1px solid #F1F5F9' }}>
                  <td style={{ padding: '10px 12px', color: '#0F1C2E', fontWeight: 500 }}>{bucketLabel(key)}</td>
                  <td style={{ padding: '10px 12px' }}>
                    {bHit
                      ? <code style={{ background: '#FFF3F3', color: '#C62828', padding: '2px 6px', borderRadius: 4 }}>{bHit}</code>
                      : <span style={{ color: '#E57373', fontWeight: 600 }}>✗ missing</span>}
                  </td>
                  <td style={{ padding: '10px 12px' }}>
                    {mHit
                      ? <code style={{ background: '#F1F8F1', color: '#2E7D32', padding: '2px 6px', borderRadius: 4 }}>{mHit}</code>
                      : <span style={{ color: '#E57373' }}>✗ missing</span>}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Class lists */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 40 }}>
        <ClassList title={`Baseline classes (${bClasses.length})`} classes={bClasses} color="#E57373" />
        <ClassList title={`ML Lens classes (${mClasses.length})`} classes={mClasses} color="#4CAF50" />
      </div>

      {/* Interpretation */}
      {(interp.baseline || interp.mllens) && (
        <div className="dashboard-section" style={{ background: '#F8FAFC', borderRadius: 8, padding: 24, border: '1px solid #E2E8F0' }}>
          <h3 className="section-title" style={{ marginBottom: 12 }}>Interpretation</h3>
          {interp.baseline && (
            <p style={{ marginBottom: 12, lineHeight: 1.7 }}
               dangerouslySetInnerHTML={{ __html: interp.baseline.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>').replace(/`([^`]+)`/g, '<code>$1</code>') }} />
          )}
          {interp.mllens && (
            <p style={{ marginBottom: 12, lineHeight: 1.7 }}
               dangerouslySetInnerHTML={{ __html: interp.mllens.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>').replace(/`([^`]+)`/g, '<code>$1</code>') }} />
          )}
          {interp.note && (
            <p style={{ color: '#4B5E78', fontSize: 13, lineHeight: 1.6, fontStyle: 'italic' }}
               dangerouslySetInnerHTML={{ __html: interp.note.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>').replace(/`([^`]+)`/g, '<code>$1</code>') }} />
          )}
        </div>
      )}
    </>
  )
}

function MetricCard({ label, baseline, mllens, delta, highlight }) {
  const deltaColor = delta?.good === true ? '#16A34A' : delta?.good === false ? '#DC2626' : '#0F1C2E'
  return (
    <div style={{
      background: highlight ? '#F0FDF4' : '#F8FAFC',
      border: `1px solid ${highlight ? '#BBF7D0' : '#E2E8F0'}`,
      borderRadius: 8,
      padding: '20px 16px',
      textAlign: 'center',
    }}>
      <div style={{ fontFamily: 'Poppins, sans-serif', fontSize: 12, color: '#4B5E78', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</div>
      <div style={{ display: 'flex', justifyContent: 'center', gap: 16, marginBottom: 8 }}>
        <span style={{ fontSize: 20 }}>{baseline}</span>
        <span style={{ color: '#CBD5E1' }}>→</span>
        <span style={{ fontSize: 20 }}>{mllens}</span>
      </div>
      <div style={{ fontFamily: 'Poppins, sans-serif', fontSize: 18, fontWeight: 700, color: deltaColor }}>{delta?.text}</div>
    </div>
  )
}

function ClassList({ title, classes, color }) {
  return (
    <div style={{ background: '#F8FAFC', borderRadius: 8, padding: 20, border: '1px solid #E2E8F0' }}>
      <h4 style={{ fontFamily: 'Poppins, sans-serif', fontSize: 13, color: '#4B5E78', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{title}</h4>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {classes.length === 0
          ? <span style={{ color: '#9CA3AF', fontSize: 13 }}>—</span>
          : classes.map(c => (
            <code key={c} style={{ background: '#fff', border: '1px solid #E2E8F0', padding: '4px 10px', borderRadius: 4, fontSize: 13, color }}>
              {c}
            </code>
          ))}
      </div>
    </div>
  )
}
