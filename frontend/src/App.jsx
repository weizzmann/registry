import React, { useEffect, useState } from 'react'
import { Routes, Route, Navigate, Link, useNavigate, useLocation } from 'react-router-dom'
import { api } from './api'
import Login from './pages/Login'
import RequestAccess from './pages/RequestAccess'
import DeloList from './pages/DeloList'
import DeloDetail from './pages/DeloDetail'
import Admin from './pages/Admin'
import Search from './pages/Search'

function ArtichokeLogo({ size = 32 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="logo-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#a5d6a7"/>
          <stop offset="100%" stopColor="#4caf50"/>
        </linearGradient>
      </defs>
      {/* Внешние листья */}
      <path d="M32 58c-9 0-18-6-18-16 0-6 3-11 7-15 3-3 6-7 8-11 1-2 2-5 3-7 1 2 2 5 3 7 2 4 5 8 8 11 4 4 7 9 7 15 0 10-9 16-18 16z" fill="url(#logo-grad)"/>
      {/* Средние листья */}
      <path d="M32 56c-7 0-14-5-14-13 0-4 2-8 5-11 2-2 4-5 6-8 1-2 2-3 3-5 1 2 2 3 3 5 2 3 4 6 6 8 3 3 5 7 5 11 0 8-7 13-14 13z" fill="#66bb6a"/>
      {/* Внутренние листья */}
      <path d="M32 54c-5 0-10-4-10-10 0-3 1-5 3-7 1-2 3-4 4-6 1-1 2-2 3-4 1 2 2 3 3 4 1 2 3 4 4 6 2 2 3 4 3 7 0 6-5 10-10 10z" fill="#81c784"/>
      {/* Блик */}
      <path d="M27 16c2-3 4-5 5-8" stroke="#e8f5e9" strokeWidth="2" strokeLinecap="round" opacity="0.5"/>
    </svg>
  )
}

export default function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    api.me().then(setUser).catch(() => setUser(null)).finally(() => setLoading(false))
  }, [location.pathname])

  const handleLogout = async () => {
    await api.logout()
    setUser(null)
    navigate('/login')
  }

  if (loading) return <div className="container"><p className="muted">Загрузка...</p></div>

  return (
    <div>
      <nav className="app-nav">
        <Link to="/" className="brand">
          <ArtichokeLogo />
          <span>Опись</span>
        </Link>
        {user && (
          <>
            <Link to="/">Дела</Link>
            <Link to="/search">Поиск</Link>
            {user.role === 'admin' && <Link to="/admin">Администрирование</Link>}
          </>
        )}
        <div className="nav-right">
          {user ? (
            <>
              <span>{user.login}</span>
              {user.department_name && (
                <span className="muted">· {user.department_name}</span>
              )}
              {user.role === 'admin' && <span className="muted">(админ)</span>}
              <button onClick={handleLogout}>Выйти</button>
            </>
          ) : (
            <Link to="/login">Войти</Link>
          )}
        </div>
      </nav>

      <div className="container">
        <Routes>
          <Route path="/login" element={user ? <Navigate to="/" /> : <Login onLogin={setUser} />} />
          <Route path="/request" element={<RequestAccess />} />
          <Route path="/" element={user ? <DeloList user={user} /> : <Navigate to="/login" />} />
          <Route path="/search" element={user ? <Search user={user} /> : <Navigate to="/login" />} />
          <Route path="/delos/:id" element={user ? <DeloDetail user={user} /> : <Navigate to="/login" />} />
          <Route path="/admin" element={user?.role === 'admin' ? <Admin /> : <Navigate to="/" />} />
        </Routes>
      </div>
    </div>
  )
}
