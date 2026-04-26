import React from 'react'

export default function StatsCard({ label, value, subtext }) {
  return (
    <div className="stats-card">
      <p className="stats-label">{label}</p>
      <p className="stats-value">{value}</p>
      {subtext && <p className="stats-subtext">{subtext}</p>}
    </div>
  )
}
