import React, { useState, useRef } from 'react'
import { Search, Cpu, Zap, Check } from 'lucide-react'
import PipelineProgress from './PipelineProgress'
import AsteriskSpinner from './AsteriskSpinner'

const API_BASE = 'http://localhost:8000'

const ARXIV_PATTERN = /(?:arxiv\.org\/(?:abs|pdf)\/|(?:doi\.org\/[\d.]+\/(?:arxiv\.)?)|^)([\d]{4}\.[\d]{4,5}(?:v\d+)?|[a-z\-]+\/\d{7})(?:$|[^\d])/i

function parseArxivId(raw) {
  const m = raw.trim().match(ARXIV_PATTERN)
  return m ? m[1] : raw.trim()
}

const HOW_STEPS = [
  {
    n: '01',
    icon: Search,
    title: 'Paste an arXiv ID',
    desc: 'Point Yukti at any paper. Just the ID from arxiv.org — no account, no upload.',
  },
  {
    n: '02',
    icon: Cpu,
    title: 'Schema is extracted',
    desc: 'Every component, tensor contract and invariant is locked into a verified manifest. A permanent record of what the paper actually says.',
  },
  {
    n: '03',
    icon: Zap,
    title: 'Explore three ways',
    desc: 'Navigate the graph, generate PyTorch code, or ask questions in plain English. Every answer is grounded in the manifest.',
  },
]

const PROOF_PAPERS = [
  {
    name: 'Differential Transformer',
    id: '2410.05258',
    rows: [
      { metric: 'Code runs', before: 'Crashes', after: 'Runs' },
      { metric: 'Drift errors', before: '4', after: '1' },
      { metric: 'Arch sections covered', before: '2 / 5', after: '5 / 5' },
    ],
  },
  {
    name: 'Grouped-Query Attention',
    id: '2305.13245',
    rows: [
      { metric: 'Code runs', before: 'Crashes', after: 'Runs' },
      { metric: 'Drift errors', before: '5', after: '4' },
      { metric: 'Arch sections covered', before: '2 / 5', after: '5 / 5' },
    ],
  },
]

function MiniDAG() {
  const NODES = [
    { label: 'Input Embedding', bg: '#EDE9FE', border: '#7C3AED', color: '#5B21B6' },
    { label: 'Multi-Head Attention', bg: '#CCFBF1', border: '#0D9488', color: '#0F766E' },
    { label: 'Add & Norm', bg: '#DBEAFE', border: '#3B82F6', color: '#1D4ED8' },
    { label: 'Feed Forward', bg: '#FEF3C7', border: '#D97706', color: '#92400E' },
    { label: 'Add & Norm', bg: '#DBEAFE', border: '#3B82F6', color: '#1D4ED8' },
    { label: 'Linear + Softmax', bg: '#FCE7F3', border: '#DB2777', color: '#9D174D' },
  ]
  return (
    <div className="mini-dag">
      {NODES.map((n, i) => (
        <React.Fragment key={i}>
          <div className="mini-dag-node" style={{ background: n.bg, borderColor: n.border, color: n.color }}>
            {n.label}
          </div>
          {i < NODES.length - 1 && <div className="mini-dag-connector" />}
        </React.Fragment>
      ))}
    </div>
  )
}

function CodePreviewMock() {
  return (
    <div className="code-preview-mock">
      <div className="code-preview-badge">
        <Check size={9} /> Grounded in the schema
      </div>
      <pre className="code-preview-pre">{`class MultiHeadAttention(nn.Module):
    # contract: [B, T, D] -> [B, T, D]
    def __init__(self, d_model=512, n_heads=8):
        self.d_k = d_model // n_heads
        self.W_q = nn.Linear(d_model, d_model)
        self.W_k = nn.Linear(d_model, d_model)
        self.W_v = nn.Linear(d_model, d_model)
        self.W_o = nn.Linear(d_model, d_model)

    def forward(self, x, mask=None):
        B, T, D = x.shape
        q = self.W_q(x).view(B, T, 8, 64)
        k = self.W_k(x).view(B, T, 8, 64)
        ...`}</pre>
    </div>
  )
}

function ChatPreviewMock() {
  return (
    <div className="chat-preview-mock">
      <div className="chat-preview-msg chat-preview-msg--user">
        What makes this attention mechanism unusual?
      </div>
      <div className="chat-preview-msg chat-preview-msg--yukti">
        <span className="chat-preview-name">Yukti</span>
        This uses <strong>differential attention</strong> — two softmax operations subtracted from each other. The subtraction cancels noise so the model focuses only on genuinely relevant tokens. The paper calls this the differential attention scalar.
      </div>
    </div>
  )
}

function LandingExplainer() {
  return (
    <section className="landing-explainer">
      <div className="landing-wave">
        <svg viewBox="0 0 1440 72" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M0,0 C480,72 960,72 1440,0 L1440,72 L0,72 Z" fill="#F8FAFC" />
        </svg>
      </div>

      <div className="landing-explainer-inner">
        {/* Feature previews — most compelling, goes first */}
        <p className="landing-section-eyebrow">What you get</p>
        <h2 className="landing-section-title">Three views into any paper</h2>
        <p className="landing-section-sub">
          Paste an arXiv ID. Yukti extracts the architecture and gives you three ways to understand it. Switch between them freely.
        </p>

        <div className="landing-previews">
          <div className="landing-preview-card">
            <div className="landing-preview-visual">
              <MiniDAG />
            </div>
            <div className="landing-preview-meta">
              <p className="landing-preview-label">Architecture DAG</p>
              <p className="landing-preview-desc">
                Every component in the paper as a live, interactive graph. Click any node to see its equations, tensor shapes, and the exact paper quote that defines it.
              </p>
            </div>
          </div>

          <div className="landing-preview-card">
            <div className="landing-preview-visual">
              <CodePreviewMock />
            </div>
            <div className="landing-preview-meta">
              <p className="landing-preview-label">Schema-Grounded Code</p>
              <p className="landing-preview-desc">
                PyTorch generated from the locked manifest, not from the LLM's training memory. Components, shapes and wiring all match the paper exactly.
              </p>
            </div>
          </div>

          <div className="landing-preview-card">
            <div className="landing-preview-visual">
              <ChatPreviewMock />
            </div>
            <div className="landing-preview-meta">
              <p className="landing-preview-label">Ask Yukti</p>
              <p className="landing-preview-desc">
                Ask anything about the paper in plain English. Yukti only knows what's in the schema, so answers are grounded, not guessed.
              </p>
            </div>
          </div>
        </div>

        {/* Proof strip */}
        <div className="landing-proof">
          <div className="landing-proof-header">
            <p className="landing-proof-title">Tested on real papers</p>
            <p className="landing-proof-sub">
              Same prompt twice. Once without context. Once with Yukti's schema injected.
            </p>
          </div>
          <div className="landing-proof-papers">
            {PROOF_PAPERS.map(p => (
              <div key={p.id} className="landing-proof-paper">
                <p className="landing-proof-paper-name">{p.name}</p>
                <p className="landing-proof-paper-id">{p.id}</p>
                <div className="landing-proof-col-heads">
                  <span className="landing-proof-col-head landing-proof-col-head--before">Without</span>
                  <span className="landing-proof-col-head landing-proof-col-head--after">With Yukti</span>
                </div>
                <div className="landing-proof-rows">
                  {p.rows.map(r => (
                    <div key={r.metric} className="landing-proof-row">
                      <span className="landing-proof-metric">{r.metric}</span>
                      <span className="landing-proof-before">{r.before}</span>
                      <span className="landing-proof-after">{r.after}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

export default function LandingPage({ onEnter }) {
  const [input, setInput] = useState('1706.03762')
  const [phase, setPhase] = useState('idle') // idle | loading | done | error
  const [pipelineDone, setPipelineDone] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)
  const fileInputRef = useRef(null)

  const handleImport = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => {
      try {
        const data = JSON.parse(ev.target.result)
        onEnter(data)
      } catch {
        setError('Invalid manifest JSON. Could not parse the file.')
        setPhase('error')
      }
    }
    reader.readAsText(file)
    e.target.value = ''
  }

  const handleSubmit = async (e) => {
    e?.preventDefault()
    const raw = input.trim()
    if (!raw || phase === 'loading') return

    setPhase('loading')
    setError(null)
    setResult(null)
    setPipelineDone(false)

    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 240_000)

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

      setTimeout(() => {
        setResult(data)
        setPhase('done')
      }, 900)

      setTimeout(() => {
        onEnter(data)
      }, 2800)
    } catch (err) {
      clearTimeout(timeoutId)
      const msg = err.name === 'AbortError'
        ? 'Request timed out (over 4 min). The LLM extractor may be overloaded. Please try again.'
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
  const components = result?.manifest?.components ?? result?.components ?? []

  return (
    <div className="landing-page">
      <div className="landing-above-fold">
      {/* Hero */}
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
          <p className="landing-tagline">
            Understand any ML paper, component by component
          </p>
        )}
      </section>

      {/* Centre stage */}
      <div className="landing-center">
        {phase === 'idle' && (
          <>
            <form className="landing-input-wrap" onSubmit={handleSubmit}>
              <input
                ref={inputRef}
                className="landing-input"
                type="text"
                placeholder="arXiv ID or URL, e.g. 1706.03762"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                autoFocus
              />
              <button className="btn-primary landing-submit-btn" type="submit" disabled={!input.trim()}>
                Research paper
              </button>
            </form>

            <div className="landing-secondary-actions">
              <button
                className="landing-sandbox-skip"
                onClick={() => onEnter(null)}
                title="Opens a pre-loaded example (Attention Is All You Need)"
              >
                or open sandbox directly →
              </button>
              <span className="landing-divider">·</span>
              <button className="landing-sandbox-skip" onClick={() => fileInputRef.current?.click()}>
                Load saved manifest .json →
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".json,application/json"
                style={{ display: 'none' }}
                onChange={handleImport}
              />
            </div>
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
                {components.length} components
              </span>
            </div>
            <h2 className="landing-result-title">
              {result.manifest?.paper?.title ?? result.paper?.title}
            </h2>
            <p className="landing-result-authors">
              {(result.manifest?.paper?.authors ?? result.paper?.authors ?? []).join(', ')}
            </p>
            <div className="landing-result-components">
              {components.map((c) => (
                <span key={c.id} className="landing-component-chip">{c.name}</span>
              ))}
            </div>
            <p className="landing-result-entering">
              Found {components.length} components. Entering schema review…
            </p>
          </div>
        )}
      </div>

      {phase === 'idle' && (
        <div className="landing-how-dark">
          <p className="landing-how-dark-title">From paper to understanding in three steps</p>
          <div className="landing-how-steps landing-how-steps--dark">
            {HOW_STEPS.map((s, i) => (
              <React.Fragment key={s.n}>
                <div className="landing-how-step">
                  <div className="landing-how-step-top">
                    <span className="landing-how-step-num">{s.n}</span>
                    <div className="landing-how-step-icon-wrap">
                      <s.icon size={18} color="rgba(255,255,255,0.75)" />
                    </div>
                  </div>
                  <p className="landing-how-step-title">{s.title}</p>
                  <p className="landing-how-step-desc">{s.desc}</p>
                </div>
                {i < HOW_STEPS.length - 1 && <div className="landing-how-connector" />}
              </React.Fragment>
            ))}
          </div>
        </div>
      )}
      </div>

      {phase === 'idle' && <LandingExplainer />}
    </div>
  )
}
