import React, { useState, useEffect } from 'react'
import { Check, X } from 'lucide-react'

const API_BASE = 'http://localhost:8000'

const DISMISSAL_KEY = 'yukti.eval.explainerDismissed'

const PAPER_INTERPRETATIONS = {
  '2410.05258': {
    baseline: `Without the schema, the model hallucinated 3 missing components and used **GroupNorm** instead of the paper's **RMSNorm**. This is a fundamental architectural error from blending DiffTransformer with vanilla Transformer patterns seen in training data.`,
    mllens: `With the locked ComponentManifest injected, the model produced all 8 correct components, correct normalization, correct FFN variant (SwiGLU), and the differential attention scalar mechanism. Drift errors dropped from 4 to 1.`,
    note: `The ML Lens generated code had a minor RoPE shape arithmetic bug (a 2-line fix). The architectural structure was fully correct. The failure was implementation arithmetic, not architectural confusion.`,
  },
  '2305.13245': {
    baseline: `Without the schema, the baseline used a dimensionally incorrect \`gather()\` to expand K/V heads. The tensor index had the wrong number of dimensions, causing a runtime crash. The paper's key invariant (K/V via \`repeat_interleave\`, not gather) was missed entirely.`,
    mllens: `With the manifest injected, the model used the correct \`repeat_interleave\` expansion and produced a model that runs and returns the right output shape (B, T, vocab_size). The manifest's \`weight_tying_mqa\` invariant directly prevented the baseline's error.`,
    note: `The ML Lens generated code is intentionally compact. It consolidates sub-components into fewer classes. Drift score reflects missing sub-module keywords, not a structural error.`,
  },
}

const GLOSSARY_TERMS = [
  {
    term: 'Hallucination Delta (dH)',
    def: 'The reduction in architectural errors when the schema is provided. Positive means the schema helped the model generate more accurate code.',
  },
  {
    term: 'Drift Errors',
    def: 'Named classes in the generated code that don\'t match any component in the paper. For example, generating GroupNorm when the paper specifies RMSNorm counts as one drift error. Lower is better.',
  },
  {
    term: 'Bucket Coverage',
    def: 'We split the architecture into required categories (attention, FFN, normalization, etc.). A bucket is covered if the generated code contains a matching layer. Gaps mean an entire architectural section was forgotten.',
  },
]

function bucketLabel(key) {
  return key.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
}

function yesno(passed) {
  if (passed === undefined || passed === null) return null
  return passed
}

function deltaStr(bVal, mVal, isBool = false) {
  if (isBool) {
    if (mVal && !bVal) return { text: '+100%', good: true }
    if (!mVal && bVal) return { text: '-100%', good: false }
    return { text: '0%', good: null }
  }
  if (bVal === 0 && mVal === 0) return { text: '0%', good: null }
  if (bVal === 0) return { text: 'worse', good: false }
  const pct = ((bVal - mVal) / bVal) * 100
  const good = pct > 0
  const sign = pct >= 0 ? '+' : ''
  return { text: `${sign}${pct.toFixed(0)}%`, good }
}

function autoSummary(bRunnable, mRunnable, bDrift, mDrift) {
  const runnableImproved = !bRunnable && mRunnable
  const driftReduced = bDrift > mDrift
  if (runnableImproved && driftReduced)
    return `The schema fixed a crash-preventing bug and reduced architectural errors from ${bDrift} to ${mDrift}.`
  if (runnableImproved)
    return `The schema made the difference between code that crashes and code that runs.`
  if (driftReduced)
    return `The schema reduced architectural errors from ${bDrift} to ${mDrift}. That is ${bDrift - mDrift} fewer invented components.`
  return `Both runs produced comparable results on this paper.`
}

export default function EvalResults({ onBack }) {
  const [papers, setPapers] = useState([])
  const [activePaper, setActivePaper] = useState(null)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [explainerDismissed, setExplainerDismissed] = useState(
    () => !!localStorage.getItem(DISMISSAL_KEY)
  )

  function dismissExplainer() {
    localStorage.setItem(DISMISSAL_KEY, '1')
    setExplainerDismissed(true)
  }

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
    <div className="eval-page-inner">
      <div className="eval-page-header">
        <div>
          <h2 className="eval-page-title">Does the Schema Reduce Hallucination?</h2>
          <p className="eval-page-subtitle">
            Comparing baseline code generation vs. schema-grounded generation on the same paper.
          </p>
        </div>
        {onBack && <button className="btn-ghost" onClick={onBack}>Back to Sandbox</button>}
      </div>

      {/* Explainer card */}
      {!explainerDismissed && (
        <div className="eval-explainer">
          <div className="eval-explainer-header">
            <p className="eval-explainer-title">What this page shows</p>
            <button className="schema-orientation-dismiss" onClick={dismissExplainer}>Got it</button>
          </div>
          <p className="eval-explainer-body">
            We ran the same prompt twice. Once with no extra context (Baseline), and once with Yukti's
            locked architecture schema injected into the context. The prompt was: "Write a PyTorch
            implementation of this paper." These are the results.
          </p>
          <div className="eval-explainer-terms">
            {GLOSSARY_TERMS.map(({ term, def }) => (
              <div key={term} className="eval-explainer-term">
                <span className="eval-term-name">{term}</span>
                <span className="eval-term-def">{def}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Paper tabs */}
      {papers.length > 0 && (
        <div className="eval-paper-tabs">
          {papers.map(pid => (
            <button
              key={pid}
              className={`eval-paper-tab ${activePaper === pid ? 'active' : ''}`}
              onClick={() => setActivePaper(pid)}
            >
              {pid}
            </button>
          ))}
        </div>
      )}

      {loading && <p className="eval-loading">Loading results…</p>}
      {error && <p className="eval-error">Error: {error}</p>}
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
  const buckets = Object.keys(required_module_keywords ?? {})
  const bCovered = b.drift?.buckets_covered ?? {}
  const mCovered = m.drift?.buckets_covered ?? {}

  const summary = autoSummary(bRunnable, mRunnable, bDrift, mDrift)

  return (
    <>
      <div className="eval-paper-info">
        <span className="eval-paper-name">{paper_title}</span>
        <code className="hash-badge">{paper_id}</code>
      </div>

      <div className="eval-paper-summary">
        {summary}
      </div>

      <div className="eval-metrics-grid">
        <MetricCard
          label="Runnable"
          tooltip="Does the generated code actually run without errors?"
          bPassed={bRunnable}
          mPassed={mRunnable}
          delta={dRunnable}
        />
        <MetricCard
          label="Shape Correct"
          tooltip="Do the tensor shapes match what the paper specifies? Wrong shapes cause crashes in production."
          bPassed={bShapes}
          mPassed={mShapes}
          delta={dShapes}
        />
        <MetricCard
          label="Drift Errors"
          tooltip="How many architectural components did the model invent that are not in the paper? Lower is better."
          bVal={String(bDrift)}
          mVal={String(mDrift)}
          delta={dDrift}
          highlight={dDrift.good}
          isCount
        />
      </div>

      {buckets.length > 0 && (
        <div className="eval-bucket-section">
          <h3 className="eval-section-title">Architecture Bucket Coverage</h3>
          <p className="eval-table-hint">
            Each row is one architectural category we require the code to implement.
            A match means the model named a class for that category. A miss means that section is absent.
          </p>
          <table className="eval-bucket-table">
            <thead>
              <tr>
                <th>Category</th>
                <th className="eval-col-baseline">Baseline</th>
                <th className="eval-col-mllens">ML Lens</th>
              </tr>
            </thead>
            <tbody>
              {buckets.map(key => {
                const bHit = bCovered[key]
                const mHit = mCovered[key]
                return (
                  <tr key={key}>
                    <td className="eval-bucket-name">{bucketLabel(key)}</td>
                    <td>
                      {bHit
                        ? <code className="eval-hit eval-hit-baseline">{bHit}</code>
                        : <span className="eval-miss"><X size={12} /> missing</span>}
                    </td>
                    <td>
                      {mHit
                        ? <code className="eval-hit eval-hit-mllens">{mHit}</code>
                        : <span className="eval-miss"><X size={12} /> missing</span>}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="eval-classes-grid">
        <ClassList title={`Baseline classes (${bClasses.length})`} classes={bClasses} variant="baseline" />
        <ClassList title={`ML Lens classes (${mClasses.length})`} classes={mClasses} variant="mllens" />
      </div>

      {(interp.baseline || interp.mllens) && (
        <div className="eval-interpretation">
          <h3 className="eval-section-title">Interpretation</h3>
          {interp.baseline && (
            <p dangerouslySetInnerHTML={{ __html: interp.baseline.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>').replace(/`([^`]+)`/g, '<code>$1</code>') }} />
          )}
          {interp.mllens && (
            <p dangerouslySetInnerHTML={{ __html: interp.mllens.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>').replace(/`([^`]+)`/g, '<code>$1</code>') }} />
          )}
          {interp.note && (
            <p className="eval-note"
               dangerouslySetInnerHTML={{ __html: interp.note.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>').replace(/`([^`]+)`/g, '<code>$1</code>') }} />
          )}
        </div>
      )}
    </>
  )
}

function MetricCard({ label, tooltip, bPassed, mPassed, bVal, mVal, delta, highlight, isCount }) {
  const deltaColor = delta?.good === true ? '#16A34A' : delta?.good === false ? '#DC2626' : '#64748B'

  function renderValue(passed, val, isML) {
    if (isCount) return <span className="metric-val">{isML ? mVal : bVal}</span>
    const ok = isML ? mPassed : bPassed
    return ok
      ? <Check size={20} color="#16A34A" />
      : <X size={20} color="#DC2626" />
  }

  return (
    <div className={`eval-metric-card ${highlight ? 'eval-metric-card--good' : ''}`}>
      <div className="eval-metric-label" title={tooltip}>{label}</div>
      <div className="eval-metric-row">
        <div className="eval-metric-col">
          <div className="eval-metric-colhead">Baseline</div>
          {renderValue(bPassed, bVal, false)}
        </div>
        <span className="eval-metric-arrow">to</span>
        <div className="eval-metric-col">
          <div className="eval-metric-colhead">ML Lens</div>
          {renderValue(mPassed, mVal, true)}
        </div>
      </div>
      <div className="eval-metric-delta" style={{ color: deltaColor }}>{delta?.text}</div>
    </div>
  )
}

function ClassList({ title, classes, variant }) {
  return (
    <div className={`eval-class-list eval-class-list--${variant}`}>
      <h4 className="eval-class-list-title">{title}</h4>
      <div className="eval-class-list-body">
        {classes.length === 0
          ? <span className="eval-class-empty">None</span>
          : classes.map(c => (
            <code key={c} className={`eval-class-chip eval-class-chip--${variant}`}>{c}</code>
          ))}
      </div>
    </div>
  )
}
