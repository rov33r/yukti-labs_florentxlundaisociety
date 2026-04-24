import React, { useState, useEffect } from 'react'
import AsteriskSpinner from './AsteriskSpinner'

const STAGES = [
  {
    id: 'resolve',
    label: 'Resolving paper',
    desc: 'Looking up arXiv metadata, authors, and PDF location',
    estimatedMs: 2000,
  },
  {
    id: 'fetch',
    label: 'Fetching PDF',
    desc: 'Downloading paper from arXiv servers',
    estimatedMs: 4000,
  },
  {
    id: 'parse',
    label: 'Parsing content',
    desc: 'Extracting text and structure with PyMuPDF',
    estimatedMs: 2500,
  },
  {
    id: 'extract',
    label: 'Extracting components',
    desc: 'Identifying model components, equations, and hyperparameters via LLM — may take 1-3 min for new papers',
    estimatedMs: 18000,
  },
  {
    id: 'lock',
    label: 'Locking schema',
    desc: 'Validating manifest and computing content hash',
    estimatedMs: 800,
  },
]

export default function PipelineProgress({ done }) {
  const [activeIdx, setActiveIdx] = useState(0)

  useEffect(() => {
    if (done) {
      setActiveIdx(STAGES.length - 1)
      return
    }

    setActiveIdx(0)
    let cumulative = 0
    const timers = STAGES.slice(0, -1).map((stage, idx) => {
      cumulative += stage.estimatedMs
      return setTimeout(() => setActiveIdx(idx + 1), cumulative)
    })

    return () => timers.forEach(clearTimeout)
  }, [done])

  const stage = STAGES[activeIdx]
  const isLast = activeIdx === STAGES.length - 1

  return (
    <div className="pipeline-track">
      {/* Step counter */}
      <div className="pipeline-counter">
        {STAGES.map((_, i) => (
          <span
            key={i}
            className={`pipeline-pip ${i < activeIdx ? 'done' : i === activeIdx ? 'active' : ''}`}
          />
        ))}
      </div>

      {/* Single animated card — key forces remount + animation on stage change */}
      <div key={stage.id} className={`pipeline-card ${done && isLast ? 'pipeline-card--done' : ''}`}>
        <div className="pipeline-card-icon">
          {done && isLast ? (
            <span className="pipeline-check">✓</span>
          ) : (
            <AsteriskSpinner size={20} color="white" />
          )}
        </div>
        <div className="pipeline-card-body">
          <span className="pipeline-card-label">{stage.label}</span>
          <span className="pipeline-card-desc">{stage.desc}</span>
        </div>
        <span className="pipeline-card-step">{activeIdx + 1} / {STAGES.length}</span>
      </div>
    </div>
  )
}
