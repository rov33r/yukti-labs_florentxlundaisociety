import React, { useState, useCallback } from 'react'
import Header from './components/Header'
import ChatPanel from './components/ChatPanel'
import Sandbox from './components/Sandbox'
import LandingPage from './components/LandingPage'
import SchemaReview from './components/SchemaReview'
import EvalResults from './components/EvalResults'
import { PARAM_DEFAULTS } from './hyperparameters'
import './index.css'

const API_BASE = 'http://localhost:8000'

export default function App() {
  const [currentPage, setCurrentPage] = useState('landing')
  const [lockedData, setLockedData] = useState(null)  // full LockedManifest from API
  const [manifest, setManifest] = useState(null)
  const [viewMode, setViewMode] = useState('model') // 'model' or 'code'

  // Hyperparams lifted here so Header (Run Traversal) can read them
  const [hyperparams, setHyperparams] = useState(() => {
    const defaults = Object.fromEntries(
      Object.entries(PARAM_DEFAULTS).map(([id, d]) => [id, { ...d }])
    )
    // Demo: show effect of increasing Multi-Head Attention heads 8 → 12
    defaults['5'] = { ...defaults['5'], num_heads: 12 }
    return defaults
  })

  const handleParamChange = useCallback((nodeId, key, value) => {
    setHyperparams((prev) => ({
      ...prev,
      [nodeId]: { ...prev[nodeId], [key]: value },
    }))
  }, [])

  const handleParamReset = useCallback((nodeId) => {
    setHyperparams((prev) => ({
      ...prev,
      [nodeId]: { ...PARAM_DEFAULTS[nodeId] },
    }))
  }, [])

  // Traversal state
  const [traversalLoading, setTraversalLoading] = useState(false)
  const [traversalResult, setTraversalResult] = useState(null)
  const [traversalError, setTraversalError]   = useState(null)

  const handleRunTraversal = useCallback(async () => {
    setTraversalLoading(true)
    setTraversalResult(null)
    setTraversalError(null)

    try {
      // Use the live ingested manifest, fall back to the sample endpoint
      let liveManifest = manifest
      if (!liveManifest) {
        const sampleRes = await fetch(`${API_BASE}/api/schema/sample`)
        if (!sampleRes.ok) throw new Error('Could not load paper manifest')
        const data = await sampleRes.json()
        liveManifest = data.manifest ?? data
      }

      const res = await fetch(`${API_BASE}/api/traverse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(liveManifest),
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Traversal failed' }))
        throw new Error(err.detail || 'Traversal failed')
      }

      setTraversalResult(await res.json())
    } catch (err) {
      setTraversalError(err.message)
    } finally {
      setTraversalLoading(false)
    }
  }, [manifest])

  const handleEnter = useCallback((data) => {
    if (data === null) {
      setCurrentPage('sandbox')
      return
    }
    setLockedData(data)
    setManifest(data?.manifest ?? data ?? null)
    setCurrentPage('schema')
  }, [])

  if (currentPage === 'landing') {
    return <LandingPage onEnter={handleEnter} />
  }

  if (currentPage === 'schema') {
    return <SchemaReview locked={lockedData} onContinue={() => setCurrentPage('sandbox')} />
  }

  if (currentPage === 'eval') {
    return (
      <div className="eval-page">
        <EvalResults onBack={() => setCurrentPage('landing')} />
      </div>
    )
  }

  return (
    <div className="app-shell">
      <Header
        viewMode={viewMode}
        setViewMode={setViewMode}
        traversalLoading={traversalLoading}
        onRunTraversal={handleRunTraversal}
        onGoEval={() => setCurrentPage('eval')}
      />
      <div className="main-split">
        <ChatPanel />
        <Sandbox
          manifest={manifest}
          viewMode={viewMode}
          hyperparams={hyperparams}
          onParamChange={handleParamChange}
          onParamReset={handleParamReset}
          traversalResult={traversalResult}
          traversalError={traversalError}
          onCloseTraversal={() => { setTraversalResult(null); setTraversalError(null) }}
        />
      </div>
    </div>
  )
}
