import React, { useEffect, useState } from 'react'
import { api } from '../api'

export default function Admin() {
  const [requests, setRequests] = useState([])
  const [users, setUsers] = useState([])
  const [departments, setDepartments] = useState([])
  const [error, setError] = useState('')

  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState(null)

  const [changingUser, setChangingUser] = useState(null)
  const [newDeptId, setNewDeptId] = useState('')

  const load = async () => {
    try {
      const [r, u, d] = await Promise.all([
        api.adminRequests(), api.adminUsers(), api.adminDepartments(),
      ])
      setRequests(r); setUsers(u); setDepartments(d)
    } catch (err) { setError(err.message) }
  }
  useEffect(() => { load() }, [])

  const sync = async () => {
    setSyncing(true); setSyncResult(null); setError('')
    try {
      const res = await api.adminSyncExternal()
      setSyncResult(res)
    } catch (err) {
      setSyncResult({ ok: false, error: err.message })
    } finally {
      setSyncing(false)
    }
  }

  const approve = async (id) => {
    const login = prompt('Логин для пользователя:')
    if (!login) return
    const password = prompt('Пароль (мин. 6 символов):')
    if (!password) return
    try {
      await api.approveRequest(id, { login, password, role: 'user' })
      load()
    } catch (err) { setError(err.message) }
  }

  const reject = async (id) => {
    if (!confirm('Отклонить заявку?')) return
    try { await api.rejectRequest(id); load() } catch (err) { setError(err.message) }
  }

  const createDept = async () => {
    const name = prompt('Название отдела:')
    if (!name) return
    try { await api.createDepartment({ name }); load() } catch (err) { setError(err.message) }
  }

  const openChangeDept = (u) => {
    setChangingUser(u)
    setNewDeptId(u.department_id)
  }

  const confirmChangeDept = async () => {
    if (!changingUser || !newDeptId) return
    try {
      await api.changeUserDepartment(changingUser.id, parseInt(newDeptId))
      setChangingUser(null)
      await load()
    } catch (err) { setError(err.message) }
  }

  return (
    <div>
      <div className="page-head">
        <h1 className="page-title">Администрирование</h1>
      </div>

      {error && <div className="error">⚠ {error}</div>}

      <div className="card">
        <div className="card-head">
          <h3>Синхронизация с внешней БД</h3>
          <button className="primary" onClick={sync} disabled={syncing}>
            {syncing ? 'Синхронизация…' : 'Синхронизировать сейчас'}
          </button>
        </div>
        <p className="muted">
          Источник: <code>data/fake_source.csv</code> · автосинхронизация каждые 6 часов
        </p>

        {syncResult && syncResult.ok && (
          <div className="success" style={{marginTop: 10}}>
            <b>Готово.</b> Добавлено: {syncResult.added}, обновлено: {syncResult.updated},
            помечено удалёнными: {syncResult.deleted}.
            Всего валидных строк в файле: {syncResult.total_in_file}.
            {syncResult.errors?.length > 0 && (
              <div className="warning" style={{marginTop: 8}}>
                <b>Предупреждения:</b>
                <ul style={{margin: '6px 0 0 18px'}}>
                  {syncResult.errors.map((e, i) => <li key={i}>{e}</li>)}
                </ul>
              </div>
            )}
          </div>
        )}
        {syncResult && !syncResult.ok && (
          <div className="error" style={{marginTop: 10}}>
            <b>Ошибка синхронизации:</b> {syncResult.error}
            {syncResult.errors?.length > 0 && (
              <ul style={{margin: '6px 0 0 18px'}}>
                {syncResult.errors.map((e, i) => <li key={i}>{e}</li>)}
              </ul>
            )}
          </div>
        )}
      </div>

      <div className="card">
        <div className="card-head">
          <h3>Заявки на доступ ({requests.length})</h3>
        </div>
        {requests.length === 0 && <p className="muted">Нет заявок</p>}
        {requests.length > 0 && (
          <table>
            <thead>
              <tr><th>Логин</th><th>Отдел</th><th>Дата</th><th></th></tr>
            </thead>
            <tbody>
              {requests.map(r => (
                <tr key={r.id}>
                  <td>{r.login}</td>
                  <td>{r.department_name || '—'}</td>
                  <td>{new Date(r.created_at).toLocaleString()}</td>
                  <td>
                    <button className="primary" onClick={() => approve(r.id)}>Одобрить</button>
                    <button style={{marginLeft: 6}} onClick={() => reject(r.id)}>Отклонить</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card">
        <div className="card-head">
          <h3>Отделы ({departments.length})</h3>
          <button onClick={createDept}>+ Создать отдел</button>
        </div>
        <table>
          <thead><tr><th>Название</th><th>Код</th></tr></thead>
          <tbody>
            {departments.map(d => (
              <tr key={d.id}><td>{d.name}</td><td>{d.code || '—'}</td></tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <div className="card-head">
          <h3>Пользователи ({users.length})</h3>
        </div>
        <table>
          <thead>
            <tr><th>Логин</th><th>Отдел</th><th>Роль</th><th>Активен</th><th></th></tr>
          </thead>
          <tbody>
            {users.map(u => (
              <tr key={u.id}>
                <td>{u.login}</td>
                <td>
                  {u.department_name || '—'}
                  <button className="ghost" style={{marginLeft: 6, fontSize: 11}}
                          onClick={() => openChangeDept(u)} title="Изменить отдел">
                    ✎
                  </button>
                </td>
                <td>{u.role}</td>
                <td>{u.is_active ? 'да' : 'нет'}</td>
                <td>
                  {u.is_active && (
                    <button onClick={() => api.deactivateUser(u.id).then(load)}>Отключить</button>
                  )}
                  <button style={{marginLeft: 6}} onClick={async () => {
                    const res = await api.resetUserPassword(u.id)
                    alert(`Новый пароль: ${res.temp_password}`)
                  }}>Сбросить пароль</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {changingUser && (
        <div className="modal-overlay" onClick={e => e.target === e.currentTarget && setChangingUser(null)}>
          <div className="modal">
            <div className="modal-header">
              <h2>Смена отдела — {changingUser.login}</h2>
              <button className="ghost" onClick={() => setChangingUser(null)}>✕</button>
            </div>
            <div className="modal-body">
              <p className="muted" style={{ marginBottom: 12 }}>
                Текущий отдел: <b>{changingUser.department_name || '—'}</b>
              </p>
              <label>
                <div className="muted" style={{ marginBottom: 4 }}>Новый отдел</div>
                <select value={newDeptId}
                        onChange={e => setNewDeptId(e.target.value)}
                        style={{ width: '100%' }}>
                  {departments.map(d => (
                    <option key={d.id} value={d.id}>{d.name}</option>
                  ))}
                </select>
              </label>
            </div>
            <div className="modal-footer">
              <button onClick={() => setChangingUser(null)}>Отмена</button>
              <button className="primary" onClick={confirmChangeDept}>Сохранить</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}