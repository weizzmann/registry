import React, { useEffect, useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

export default function DeloList({ user }) {
  const [delos, setDelos] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)

  const currentYear = new Date().getFullYear()
  const [selectedYear, setSelectedYear] = useState('all')
  const [filterExpanded, setFilterExpanded] = useState(false)
  const [expandedYear, setExpandedYear] = useState(currentYear)
  const [form, setForm] = useState({ base_title: '', year: currentYear })
  const [error, setError] = useState('')

  const isAdmin = user?.role === 'admin'

  const load = () => {
    setLoading(true)
    api.listDelos().then(setDelos).finally(() => setLoading(false))
  }
  useEffect(load, [])

  const availableYears = useMemo(() => {
    const years = new Set(delos.map(d => d.year))
    years.add(currentYear)
    return Array.from(years).sort((a, b) => b - a)
  }, [delos, currentYear])

  // При первой загрузке раскрываем год, в котором есть данные
  // (текущий год, если в нём есть дела; иначе самый свежий с данными)
  useEffect(() => {
    if (delos.length === 0) return
    const years = Array.from(new Set(delos.map(d => d.year))).sort((a, b) => b - a)
    const defYear = years.includes(currentYear) ? currentYear : years[0]
    if (defYear) setExpandedYear(defYear)
  }, [delos.length])

  const grouped = useMemo(() => {
    const filtered = selectedYear === 'all'
      ? delos
      : delos.filter(d => d.year === selectedYear)

    const map = new Map()
    for (const d of filtered) {
      if (!map.has(d.year)) map.set(d.year, [])
      map.get(d.year).push(d)
    }
    return Array.from(map.entries())
      .sort((a, b) => b[0] - a[0])
      .map(([year, list]) => [
        year,
        list.sort((a, b) => a.base_title.localeCompare(b.base_title, 'ru')),
      ])
  }, [delos, selectedYear])

  const openCreateModal = () => {
    setForm({
      base_title: '',
      year: selectedYear === 'all' ? currentYear : selectedYear,
    })
    setError('')
    setShowCreate(true)
  }

  const create = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await api.createDelo(form)
      setShowCreate(false)
      setSelectedYear(form.year)
      setExpandedYear(form.year)
      setForm({ base_title: '', year: form.year })
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const toggleYear = (year) => {
    setExpandedYear(expandedYear === year ? null : year)
  }

  const totalCount = grouped.reduce((s, [, list]) => s + list.length, 0)
  const otherYearsCount = availableYears.filter(y => y !== currentYear).length

  return (
    <div>
      <div className="page-head">
        <h1 className="page-title">{isAdmin ? 'Все дела' : 'Дела'}</h1>
        {!isAdmin && (
          <button className="primary" onClick={openCreateModal}>+ Создать дело</button>
        )}
      </div>

      <div className="card" style={{ padding: '12px 20px', marginBottom: 16 }}>
        <div className="row" style={{ alignItems: 'center', flexWrap: 'wrap' }}>
          <span className="muted" style={{ marginRight: 8 }}>Год:</span>
          <button
            className={selectedYear === 'all' ? 'primary' : ''}
            onClick={() => setSelectedYear('all')}
          >
            Все
          </button>
          <button
            className={selectedYear === currentYear ? 'primary' : ''}
            onClick={() => setSelectedYear(currentYear)}
          >
            {currentYear}
          </button>
          {filterExpanded && availableYears.filter(y => y !== currentYear).map(y => (
            <button
              key={y}
              className={selectedYear === y ? 'primary' : ''}
              onClick={() => setSelectedYear(y)}
              style={{ minWidth: 60 }}
            >
              {y}
            </button>
          ))}
          {otherYearsCount > 0 && (
            <button
              className="ghost"
              onClick={() => setFilterExpanded(v => !v)}
            >
              {filterExpanded ? '▴ Свернуть' : `▾ Ещё ${otherYearsCount}`}
            </button>
          )}
        </div>
      </div>

      {loading ? <p className="muted">Загрузка...</p> : (
        <div className="card">
          <div className="card-head">
            <h3>
              {selectedYear === 'all' ? 'Все дела' : `Дела за ${selectedYear} год`}
            </h3>
            <span className="muted">всего: {totalCount}</span>
          </div>

          {totalCount === 0 && (
            <p className="muted" style={{ textAlign: 'center', padding: 20 }}>
              {selectedYear === 'all'
                ? 'Дел пока нет. Создайте первое.'
                : `В ${selectedYear} году дел ещё нет.`}
            </p>
          )}

          {totalCount > 0 && (
            <table>
              <thead>
                <tr>
                  <th>Название</th>
                  {isAdmin && <th style={{ width: 180 }}>Отдел</th>}
                  <th style={{ width: 120 }}>Статус</th>
                  <th style={{ width: 140 }}></th>
                </tr>
              </thead>
              <tbody>
                {grouped.map(([year, list]) => {
                  const isExpanded = expandedYear === year
                  const showHeader = selectedYear === 'all'
                  return (
                    <React.Fragment key={year}>
                      {showHeader && (
                        <tr
                          className="year-header"
                          style={{ cursor: 'pointer' }}
                          onClick={() => toggleYear(year)}
                        >
                          <td colSpan={isAdmin ? 4 : 3}>
                            <span style={{
                              display: 'inline-block',
                              width: 14,
                              marginRight: 6,
                              color: 'var(--primary)',
                              fontSize: 12,
                            }}>
                              {isExpanded ? '▾' : '▸'}
                            </span>
                            <span className="year-label">{year} год</span>
                            <span style={{
                              marginLeft: 14,
                              fontSize: 12,
                              fontWeight: 500,
                              color: 'var(--text-muted)',
                              textTransform: 'none',
                              letterSpacing: 0,
                            }}>
                              всего: {list.length}
                            </span>
                          </td>
                        </tr>
                      )}
                      {(showHeader ? isExpanded : true) && list.map(d => (
                        <tr key={d.id}>
                          <td><b>{d.full_title}</b></td>
                          {isAdmin && <td>{d.department_name || '—'}</td>}
                          <td>
                            <span className={`badge ${d.status}`}>
                              {d.status === 'open' ? 'Открыто' : 'Закрыто'}
                            </span>
                          </td>
                          <td style={{ textAlign: 'right' }}>
                            <Link to={`/delos/${d.id}`}>
                              <button className="ghost">
                                {isAdmin ? 'Просмотр →' : 'Открыть →'}
                              </button>
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </React.Fragment>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      )}

      {showCreate && (
        <div className="modal-overlay" onClick={e => e.target === e.currentTarget && setShowCreate(false)}>
          <div className="modal">
            <div className="modal-header">
              <h2>Создание дела</h2>
              <button className="ghost" onClick={() => setShowCreate(false)}>✕</button>
            </div>
            <form onSubmit={create}>
              <div className="modal-body">
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <label>
                    <div className="muted" style={{ marginBottom: 4 }}>
                      Номер или название (напр. 23/56)
                    </div>
                    <input
                      placeholder="23/56"
                      value={form.base_title}
                      onChange={e => setForm({ ...form, base_title: e.target.value })}
                      required
                      style={{ width: '100%' }}
                      autoFocus
                    />
                  </label>
                  <label>
                    <div className="muted" style={{ marginBottom: 4 }}>Год</div>
                    <input
                      type="number"
                      value={form.year}
                      onChange={e => setForm({ ...form, year: parseInt(e.target.value) || currentYear })}
                      required
                      style={{ width: '100%' }}
                    />
                  </label>
                  <div className="muted" style={{ fontSize: 12 }}>
                    Полное название: <b>Дело № {form.base_title || '...'}-{form.year}</b>
                  </div>
                  <div className="warning" style={{ fontSize: 12 }}>
                    ⓘ Если в системе уже есть <b>незакрытое</b> дело с таким же названием
                    (за любой год) — сначала завершите его, затем создавайте новое.
                  </div>
                </div>
                {error && (
                  <div className="error" style={{ marginTop: 12 }}>
                    ⚠ {error}
                  </div>
                )}
              </div>
              <div className="modal-footer">
                <button type="button" onClick={() => setShowCreate(false)}>Отмена</button>
                <button type="submit" className="primary">Создать</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
