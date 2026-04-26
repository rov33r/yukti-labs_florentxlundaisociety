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
        <ChatPanel manifest={manifest} />
        <Sandbox manifest={manifest} viewMode={viewMode} />
      </div>
    </div>
  )
}
