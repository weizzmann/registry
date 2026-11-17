import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

export default function RequestAccess() {
  const [departments, setDepartments] = useState([])
  const [login, setLogin] = useState('')
  const [email, setEmail] = useState('')
  const [deptId, setDeptId] = useState('')
  const [message, setMessage] = useState('')
  const [status, setStatus] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.publicDepartments().then(setDepartments).catch(() => {})
  }, [])

  const submit = async (e) => {
    e.preventDefault()
    setError(''); setStatus(null)
    try {
      await api.requestAccess({
        login, email: email || null,
        department_id: parseInt(deptId),
        message: message || null,
      })
      setStatus('Заявка отправлена. Администратор создаст учётную запись.')
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="card" style={{maxWidth:500, margin:'40px auto'}}>
      <h2 style={{marginBottom:16}}>Запрос доступа</h2>
      <form onSubmit={submit} style={{display:'flex', flexDirection:'column', gap:10}}>
        <input placeholder="Желаемый логин" value={login} onChange={e => setLogin(e.target.value)} />
        <input placeholder="Email (опционально)" value={email} onChange={e => setEmail(e.target.value)} />
        <select value={deptId} onChange={e => setDeptId(e.target.value)} required>
          <option value="">— выберите отдел —</option>
          {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
        <textarea placeholder="Комментарий (опционально)" value={message}
                  onChange={e => setMessage(e.target.value)} rows={3} />
        {error && <div className="error">{error}</div>}
        {status && <div className="success">{status}</div>}
        <button className="primary" type="submit">Отправить заявку</button>
      </form>
      <p style={{marginTop:16, fontSize:14}}>
        <Link to="/login">← К входу</Link>
      </p>
    </div>
  )
}