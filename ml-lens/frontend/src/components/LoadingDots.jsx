import React from 'react'
import AsteriskSpinner from './AsteriskSpinner'

export default function LoadingDots() {
  return (
    <span className="loading-inline">
      <AsteriskSpinner size={14} color="#7A93B0" />
      <span className="loading-inline-label">Thinking…</span>
    </span>
  )
}
