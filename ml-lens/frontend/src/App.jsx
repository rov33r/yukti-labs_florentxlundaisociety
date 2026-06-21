import React, { useState, useCallback } from 'react'
import Header from './components/Header'
import ChatPanel from './components/ChatPanel'
import Sandbox from './components/Sandbox'
import LandingPage from './components/LandingPage'
import SchemaReview from './components/SchemaReview'
import EvalResults from './components/EvalResults'
import './index.css'

export default function App() {
  const [currentPage, setCurrentPage] = useState('landing')
  const [lockedData, setLockedData] = useState(null)
  const [manifest, setManifest] = useState(null)
  const [viewMode, setViewMode] = useState('model')

  const handleExport = useCallback(() => {
    if (!manifest) return
    const json = JSON.stringify(manifest, null, 2)
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${manifest.paper?.arxiv_id ?? 'manifest'}.json`
    a.click()
    URL.revokeObjectURL(url)
  }, [manifest])

  const handleGoHome = useCallback(() => {
    setCurrentPage('landing')
    setLockedData(null)
    setManifest(null)
  }, [])

  const handleEnter = useCallback((data) => {
    if (data === null) {
      setCurrentPage('sandbox')
      return
    }
    setLockedData(data)
    setManifest(data?.manifest ?? data ?? null)
    setCurrentPage('schema')
  }, [])

  const handleAction = useCallback((action) => {
    if (!action?.type || !action?.payload) return
    const { type, payload } = action

    setManifest((prev) => {
      if (!prev) return prev
      const components = [...(prev.components ?? [])]

      if (type === 'add_component') {
        if (components.find((c) => c.id === payload.id)) return prev
        components.push({
          id: payload.id,
          name: payload.name ?? payload.id,
          kind: payload.kind ?? 'other',
          description: payload.description ?? '',
          operations: payload.operations ?? [],
          depends_on: payload.depends_on ?? [],
          hyperparameters: {},
          equations: [],
        })
      } else if (type === 'remove_component') {
        const idx = components.findIndex((c) => c.id === payload.id)
        if (idx === -1) return prev
        components.splice(idx, 1)
        components.forEach((c) => {
          c.depends_on = (c.depends_on ?? []).filter((d) => d !== payload.id)
        })
      } else if (type === 'update_component') {
        const comp = components.find((c) => c.id === payload.id)
        if (!comp) return prev
        const { id: _id, ...fields } = payload
        Object.assign(comp, fields)
      } else if (type === 'duplicate_component') {
        const src = components.find((c) => c.id === payload.sourceId)
        if (!src) return prev
        components.push({
          ...src,
          id: payload.newId,
          name: payload.name ?? `${src.name} (copy)`,
          depends_on: payload.depends_on ?? src.depends_on ?? [],
        })
      }

      return { ...prev, components }
    })
  }, [])

  if (currentPage === 'landing') {
    return <LandingPage onEnter={handleEnter} />
  }

  if (currentPage === 'schema') {
    return <SchemaReview locked={lockedData} onContinue={() => setCurrentPage('sandbox')} onBack={handleGoHome} />
  }

  if (currentPage === 'eval') {
    return (
      <div className="eval-page">
        <EvalResults onBack={() => setCurrentPage('sandbox')} />
      </div>
    )
  }

  return (
    <div className="app-shell">
      <Header
        viewMode={viewMode}
        setViewMode={setViewMode}
        onGoEval={() => setCurrentPage('eval')}
        onExport={manifest ? handleExport : null}
        onGoHome={handleGoHome}
        manifest={manifest}
      />
      <div className="main-split">
        <ChatPanel manifest={manifest} onAction={handleAction} />
        <Sandbox manifest={manifest} viewMode={viewMode} onGoHome={handleGoHome} />
      </div>
    </div>
  )
}
