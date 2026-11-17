import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

export default function Login({ onLogin }) {
  const [login, setLogin] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    try {
      const user = await api.login(login, password)
      onLogin(user)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="card" style={{maxWidth:400, margin:'40px auto'}}>
      <h2 style={{marginBottom:16}}>Вход</h2>
      <form onSubmit={submit} style={{display:'flex', flexDirection:'column', gap:10}}>
        <input placeholder="Логин" value={login} onChange={e => setLogin(e.target.value)} />
        <input type="password" placeholder="Пароль" value={password}
               onChange={e => setPassword(e.target.value)} />
        {error && <div className="error">{error}</div>}
        <button className="primary" type="submit">Войти</button>
      </form>
      <p style={{marginTop:16, fontSize:14}}>
        Нет доступа? <Link to="/request">Запросить</Link>
      </p>
    </div>
  )
}