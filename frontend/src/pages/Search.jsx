import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

const PAGE_SIZE = 50

export default function Search({ user }) {
  const [q, setQ] = useState('')
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState('')

  const isAdmin = user?.role === 'admin'

  const doSearch = async (query) => {
    const trimmed = query.trim()
    if (trimmed.length < 2) { setItems([]); setTotal(0); return }
    setLoading(true); setError('')
    try {
      const res = await api.searchDocuments(trimmed, PAGE_SIZE, 0)
      setItems(res.items); setTotal(res.total); setHasMore(res.has_more); setOffset(res.items.length)
    } catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }

  const loadMore = async () => {
    setLoadingMore(true)
    try {
      const res = await api.searchDocuments(q.trim(), PAGE_SIZE, offset)
      setItems(prev => [...prev, ...res.items]); setHasMore(res.has_more); setOffset(offset + res.items.length)
    } catch (e) { setError(e.message) }
    finally { setLoadingMore(false) }
  }

  useEffect(() => {
    const timer = setTimeout(() => doSearch(q), 300)
    return () => clearTimeout(timer)
  }, [q])

  const trimmed = q.trim()

  return (
    <div>
      <div className="page-head"><h1 className="page-title">Поиск документов</h1></div>
      {error && <div className="error">⚠ {error}</div>}

      <div className="card">
        <input placeholder="Поиск по названию, номерам, органу..." value={q} onChange={e => setQ(e.target.value)} style={{ width: '100%', fontSize: 15, padding: '10px 14px' }} autoFocus />
        <p className="muted" style={{ marginTop: 8, fontSize: 12 }}>
          {isAdmin ? 'Поиск по всем отделам' : 'Поиск по документам вашего отдела'} · минимум 2 символа
        </p>
      </div>

      {loading && <div className="card"><p className="muted">Поиск...</p></div>}
      {!loading && trimmed.length >= 2 && items.length === 0 && (
        <div className="card"><p className="muted" style={{ textAlign: 'center', padding: 20 }}>Ничего не найдено</p></div>
      )}

      {!loading && items.length > 0 && (
        <div className="card">
          <div className="card-head"><h3>Найдено: {total}</h3></div>
          <table>
            <thead>
              <tr><th>Документ</th><th>Где находится</th><th style={{ width: 130 }}></th></tr>
            </thead>
            <tbody>
              {items.map(it => (
                <tr key={it.id}>
                  <td>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, alignItems: 'center' }}>
                      <span>{it.title}</span>
                      {it.doc_num && <span style={{color: '#666'}}>№{it.doc_num}</span>}
                      {it.organ && <span style={{color: '#666'}}>, {it.organ}</span>}
                      {it.is_changed && <span className="badge" style={{ backgroundColor: '#fff3cd', color: '#856404', fontSize: 10 }}>Изменено</span>}
                    </div>
                    {it.is_changed && (
                      <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>
                        Было: {it.original_title} {it.original_doc_num ? `№${it.original_doc_num}` : ''}
                      </div>
                    )}
                  </td>
                  <td><span className="pages" style={{ fontSize: 12 }}>{it.location}</span></td>
                  <td style={{ textAlign: 'right' }}><Link to={`/delos/${it.delo_id}`}><button className="ghost">Открыть дело →</button></Link></td>
                </tr>
              ))}
            </tbody>
          </table>
          {hasMore && <div style={{ textAlign: 'center', marginTop: 12 }}><button onClick={loadMore} disabled={loadingMore}>{loadingMore ? 'Загрузка...' : `Показать ещё ${PAGE_SIZE}`}</button></div>}
        </div>
      )}
    </div>
  )
}
