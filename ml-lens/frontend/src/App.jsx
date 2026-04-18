import React, { useState } from 'react'
import Header from './components/Header'
import ChatPanel from './components/ChatPanel'
import Sandbox from './components/Sandbox'
import LandingPage from './components/LandingPage'
import './index.css'

export default function App() {
  const [currentPage, setCurrentPage] = useState('landing')

  if (currentPage === 'landing') {
    return <LandingPage onEnter={() => setCurrentPage('sandbox')} />
  }

  return (
    <div className="app-shell">
      <Header />
      <div className="main-split">
        <ChatPanel />
        <Sandbox />
      </div>
    </div>
  )
}
