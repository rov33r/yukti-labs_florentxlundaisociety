import React from 'react'
import Header from './components/Header'
import ChatPanel from './components/ChatPanel'
import Sandbox from './components/Sandbox'
import './index.css'

export default function App() {
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
