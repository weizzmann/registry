import React, { useEffect, useState } from 'react'
import { Routes, Route, Navigate, Link, useNavigate, useLocation } from 'react-router-dom'
import { api } from './api'
import Login from './pages/Login'
import RequestAccess from './pages/RequestAccess'
import DeloList from './pages/DeloList'
import DeloDetail from './pages/DeloDetail'
import Admin from './pages/Admin'
import Search from './pages/Search'

function ArtichokeLogo({ size = 22 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Основной контур (листья) */}
      <path d="M12 22c-4.5 0-8-3.5-8-8 0-5 3-9.5 8-13 5 3.5 8 8 8 13 0 4.5-3.5 8-8 8z" 
            stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
      {/* Внутренние слои (чешуйки) */}
      <path d="M12 22V9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M7 14c2 1.5 5 1.5 5 1.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M17 14c-2 1.5-5 1.5-5 1.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M9 10c1.5 1 3 1 3 1" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M15 10c-1.5 1-3 1-3 1" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      {/* Верхушка */}
      <path d="M12 9V5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
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