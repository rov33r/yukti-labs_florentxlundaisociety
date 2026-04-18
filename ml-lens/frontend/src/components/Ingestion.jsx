import React, { useState } from 'react'
import IngestionForm from './IngestionForm'
import IngestionResult from './IngestionResult'
import LoadingBar from './LoadingBar'
import LoadingDots from './LoadingDots'

const API_BASE = 'http://localhost:8000'

export default function Ingestion() {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const handleIngest = async (url, forceRefresh) => {
    setLoading(true)
    setError(null)

    try {
      const res = await fetch(`${API_BASE}/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, force_refresh: forceRefresh })
      })

      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Ingestion failed')
      }

      const data = await res.json()
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setResult(null)
    setError(null)
  }

  return (
    <div className="ingestion-page">
      <LoadingBar loading={loading} label="Processing paper…" />

      <div className="ingestion-container">
        <h2>Paper Ingestion</h2>
        <p className="page-subtitle">Extract components from arXiv papers</p>

        {error && (
          <div className="alert alert-error">
            <p>{error}</p>
          </div>
        )}

        {result ? (
          <IngestionResult result={result} onReset={handleReset} />
        ) : (
          <>
            <IngestionForm onSubmit={handleIngest} loading={loading} />
          </>
        )}
      </div>
    </div>
  )
}
