import React from 'react'
import AsteriskSpinner from './AsteriskSpinner'

export default function LoadingBar({ loading, label = 'Loading…' }) {
  if (!loading) return null
  return (
    <div className="loading-indicator">
      <AsteriskSpinner size={18} />
      <span className="loading-indicator-label">{label}</span>
    </div>
  )
}
