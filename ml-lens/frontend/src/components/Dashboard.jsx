import React, { useState, useEffect } from 'react'
import Card from './Card'
import StatsCard from './StatsCard'

export default function Dashboard() {
  const [stats, setStats] = useState([])
  const [evaluations, setEvaluations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const API_BASE = 'http://localhost:8000'

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, evalsRes] = await Promise.all([
          fetch(`${API_BASE}/api/stats`),
          fetch(`${API_BASE}/api/evaluations`)
        ])

        if (!statsRes.ok || !evalsRes.ok) {
          throw new Error('Failed to fetch data')
        }

        const statsData = await statsRes.json()
        const evalsData = await evalsRes.json()

        setStats(statsData)
        setEvaluations(evalsData)
        setLoading(false)
      } catch (err) {
        setError(err.message)
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  if (loading) {
    return (
      <div className="dashboard">
        <p className="loading">Loading dashboard...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="dashboard">
        <p className="error">Error: {error}</p>
        <p className="error-hint">Make sure the backend is running on http://localhost:8000</p>
      </div>
    )
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h2>Dashboard</h2>
        <button className="btn-primary">+ New Evaluation</button>
      </div>

      <div className="stats-grid">
        {stats.map((stat, idx) => (
          <StatsCard key={idx} {...stat} />
        ))}
      </div>

      <div className="dashboard-section">
        <h3 className="section-title">Recent Evaluations</h3>
        <div className="evals-list">
          {evaluations.map(evaluation => (
            <Card key={evaluation.id} title={evaluation.name}>
              <div className="eval-row">
                <span className={`badge badge-${evaluation.status}`}>
                  {evaluation.status}
                </span>
                {evaluation.score && (
                  <span className="eval-score">{evaluation.score}</span>
                )}
              </div>
            </Card>
          ))}
        </div>
      </div>
    </div>
  )
}
