import React from 'react'

export default function Header() {
  return (
    <header className="header">
      <div className="header-container">
        <h1 className="logo">Yukti</h1>
        <div className="header-actions">
          <button className="btn-ghost">Run Traversal</button>
          <button className="btn-primary">Export</button>
        </div>
      </div>
    </header>
  )
}
