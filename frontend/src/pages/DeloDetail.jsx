import React, { useEffect, useState, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api'

function formatPages(start, end) {
  if (start == null || end == null) return '—'
  return start === end ? String(start) : `${start}–${end}`
}

function docLabel(title, docNum, organ) {
  let parts = [];
  if (title) parts.push(title);
  if (docNum) parts.push(`№${docNum}`);
  let str = parts.join(' ');
  if (organ) str += `, ${organ}`;
  return str || '—';
}

function StatusBadge({ status }) {
  const labels = { open: 'Открыт', full: 'Заполнен', final: 'Финальный', closed: 'Закрыто' }
  return <span className={`badge ${status}`}>{labels[status] || status}</span>
}

function Modal({ title, onClose, children, footer, wide, headerRight }) {
  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className={`modal ${wide ? 'wide' : ''}`}>
        <div className="modal-header">
          <h2>{title}</h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {headerRight}
            <button className="ghost" onClick={onClose}>✕</button>
          </div>
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-footer">{footer}</div>}
      </div>
    </div>
  )
}

const PAGE_SIZE = 50

function SelectDocumentsModal({ deloId, currentTom, onSave, onClose, onError }) {
  const [search, setSearch] = useState('')
  const [filterDateFrom, setFilterDateFrom] = useState('')
  const [filterDateTo, setFilterDateTo] = useState('')
  const [filterOrgan, setFilterOrgan] = useState('')
  const [filterEmployee, setFilterEmployee] = useState('')
  const [showFilters, setShowFilters] = useState(false)

  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [selected, setSelected] = useState([])
  const [manual, setManual] = useState([])
  const [busy, setBusy] = useState(false)
  const [showManualModal, setShowManualModal] = useState(false)

  const tomExists = currentTom && currentTom.id
  const tomNumber = tomExists ? currentTom.tom_number : '—'
  const maxPages = currentTom?.max_pages || 250
  const currentEnd = currentTom?.current_end || 0
  const freePages = currentTom?.free_pages ?? maxPages

  const selectedExternalPages = selected.reduce((s, x) => s + x.page_count, 0)
  const manualPages = manual.reduce((s, x) => s + x.page_count, 0)
  const selectedPages = selectedExternalPages + manualPages
  const selectedCount = selected.length + manual.length

  const remaining = freePages - selectedPages
  const fits = selectedPages <= freePages

  const loadFirst = async (query) => {
    setLoading(true)
    try {
      const res = await api.listExternal({
        search: query || '',
        unplaced_only: 'false',
        limit: PAGE_SIZE,
        offset: 0,
        date_from: filterDateFrom || undefined,
        date_to: filterDateTo || undefined,
        organ: filterOrgan || undefined,
        employee: filterEmployee || undefined,
      })
      setItems(res.items)
      setTotal(res.total)
      setHasMore(res.has_more)
      setOffset(res.items.length)
    } catch (e) { onError(e.message) }
    finally { setLoading(false) }
  }

  const loadMore = async () => {
    setLoadingMore(true)
    try {
      const res = await api.listExternal({
        search: search || '',
        unplaced_only: 'false',
        limit: PAGE_SIZE,
        offset,
        date_from: filterDateFrom || undefined,
        date_to: filterDateTo || undefined,
        organ: filterOrgan || undefined,
        employee: filterEmployee || undefined,
      })
      setItems(prev => [...prev, ...res.items])
      setHasMore(res.has_more)
      setOffset(offset + res.items.length)
    } catch (e) { onError(e.message) }
    finally { setLoadingMore(false) }
  }

  useEffect(() => {
    const timer = setTimeout(() => loadFirst(search), 300)
    return () => clearTimeout(timer)
  }, [search, filterDateFrom, filterDateTo, filterOrgan, filterEmployee])

  const isSelected = (ref) => selected.some(s => s.external_ref === ref)

  const toggle = (c) => {
    if (isSelected(c.external_ref)) {
      setSelected(selected.filter(s => s.external_ref !== c.external_ref))
    } else {
      setSelected([...selected, c]) // Сохраняем ВЕСЬ объект для отображения
    }
  }

  const selectAllOnPage = () => {
    const available = items.filter(c => !c.placed)
    const newSelected = [...selected]
    for (const c of available) {
      if (!isSelected(c.external_ref)) {
        newSelected.push(c)
      }
    }
    setSelected(newSelected)
  }

  const clearSelected = () => setSelected([])

  const save = async () => {
    setBusy(true); onError('')
    try {
      const payload = [
        ...selected.map(s => ({ source: 'external', external_ref: s.external_ref })),
        ...manual,
      ]
      await onSave(payload)
    } catch (err) { onError(err.message) }
    finally { setBusy(false) }
  }

  const [draggedIdx, setDraggedIdx] = useState(null)
  const [dragOverIdx, setDragOverIdx] = useState(null)

  const handleDrop = (from, to) => {
    const arr = [...selected]
    const [moved] = arr.splice(from, 1)
    arr.splice(to, 0, moved)
    setSelected(arr)
  }

  return (
    <>
      <Modal
        title={`Выбор документов — найдено: ${total}`}
        onClose={onClose}
        wide
        headerRight={
          <button className="ghost" onClick={() => setShowManualModal(true)}>
            + Добавить вручную
          </button>
        }
        footer={
          <>
            <span className="muted" style={{marginRight: 'auto'}}>
              {tomExists ? `Том ${tomNumber}: ` : 'Том ещё не создан: '}
              свободно {freePages} л. · выбрано {selectedPages} л.
              {selectedPages > 0 && (
                <span style={{marginLeft: 6, color: fits ? '#1e7d3e' : '#c0392b', fontWeight: 600}}>
                  ({fits ? `останется ${remaining} л.` : `не хватает ${-remaining} л.`})
                </span>
              )}
            </span>
            <button onClick={onClose}>Отмена</button>
            <button className="primary" onClick={save} disabled={busy || selectedCount === 0}>
              Сохранить выбор ({selectedCount})
            </button>
          </>
        }
      >
        <div style={{
          display: 'flex', gap: 16, flexWrap: 'wrap',
          padding: '10px 14px', marginBottom: 12,
          background: fits && selectedPages > 0 ? '#f5fcf7' : !fits ? '#fdf3f3' : '#f8f9fc',
          border: `1px solid ${fits && selectedPages > 0 ? '#b6e0c2' : !fits ? '#f0c0c0' : '#e2e6ee'}`,
          borderRadius: 6, fontSize: 13,
        }}>
          <div>
            <span className="muted">Целевой том: </span>
            <b>{tomExists ? `№ ${tomNumber}` : 'будет создан'}</b>
            <span className="muted"> ({currentEnd}/{maxPages})</span>
          </div>
          <div><span className="muted">Свободно: </span><b>{freePages} л.</b></div>
          <div>
            <span className="muted">Выбрано: </span>
            <b>{selectedPages} л.</b>
            {selectedCount > 0 && <span className="muted"> ({selectedCount} док.)</span>}
          </div>
        </div>

        <div className="row" style={{ marginBottom: 12 }}>
          <input placeholder="Поиск по названию, номерам, шифру..." value={search} onChange={e => setSearch(e.target.value)} style={{flex: 1}} />
          <button className="ghost" onClick={() => setShowFilters(!showFilters)}>
            {showFilters ? 'Скрыть фильтры' : 'Фильтры'}
          </button>
        </div>

        {showFilters && (
          <div style={{ display: 'flex', gap: 10, marginBottom: 12, padding: 12, background: '#f8f9fc', borderRadius: 6, flexWrap: 'wrap' }}>
            <label style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 12 }}>
              <span className="muted">Дата с</span>
              <input type="date" value={filterDateFrom} onChange={e => setFilterDateFrom(e.target.value)} />
            </label>
            <label style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 12 }}>
              <span className="muted">Дата по</span>
              <input type="date" value={filterDateTo} onChange={e => setFilterDateTo(e.target.value)} />
            </label>
            <label style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 12, flex: 1 }}>
              <span className="muted">Орган (через запятую)</span>
              <input placeholder="УУР, УЭБ..." value={filterOrgan} onChange={e => setFilterOrgan(e.target.value)} />
            </label>
            <label style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 12, flex: 1 }}>
              <span className="muted">Сотрудник (через запятую)</span>
              <input placeholder="188, 331..." value={filterEmployee} onChange={e => setFilterEmployee(e.target.value)} />
            </label>
            <button className="ghost danger" style={{ marginTop: 18 }} onClick={() => { setFilterDateFrom(''); setFilterDateTo(''); setFilterOrgan(''); setFilterEmployee(''); }}>
              Сбросить
            </button>
          </div>
        )}

        {(selected.length > 0 || manual.length > 0) && (
          <div className="selected-box" style={{ marginBottom: 12 }}>
            <div className="row" style={{ justifyContent: 'space-between', marginBottom: 8 }}>
              <b>Выбрано ({selectedCount}):</b>
              <button className="ghost danger" onClick={() => { clearSelected(); setManual([]) }}>Очистить всё</button>
            </div>
            <ul style={{ maxHeight: 200, overflowY: 'auto' }}>
              {selected.map((s, i) => (
                <li key={s.external_ref} draggable onDragStart={(e) => { if (e.target.tagName === 'INPUT' || e.target.tagName === 'BUTTON') { e.preventDefault(); return; } setDraggedIdx(i); e.dataTransfer.effectAllowed = 'move'; }} onDragOver={(e) => { e.preventDefault(); if (draggedIdx !== null && draggedIdx !== i) setDragOverIdx(i); }} onDragLeave={() => setDragOverIdx(null)} onDrop={(e) => { e.preventDefault(); if (draggedIdx !== null && draggedIdx !== i) handleDrop(draggedIdx, i); setDraggedIdx(null); setDragOverIdx(null); }} onDragEnd={() => { setDraggedIdx(null); setDragOverIdx(null); }} style={{ opacity: draggedIdx === i ? 0.3 : 1, backgroundColor: dragOverIdx === i ? '#e8efff' : undefined, cursor: 'grab' }}>
                  <span style={{display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap'}}>
                    <span style={{color: '#aaa', fontSize: 16}}>≡</span>
                    <b>{s.title}</b>
                    {s.doc_num && <span style={{color: '#666'}}>№{s.doc_num}</span>}
                    {s.organ && <span style={{color: '#666'}}>, {s.organ}</span>}
                    <span className="muted">({s.page_count} л.)</span>
                  </span>
                  <button className="ghost danger" onClick={() => setSelected(selected.filter(x => x.external_ref !== s.external_ref))}>✕</button>
                </li>
              ))}
              {manual.map((m, i) => (
                <li key={`manual-${i}`}>
                  <span style={{display: 'flex', alignItems: 'center', gap: 6}}>
                    <span className="badge manual-badge">вручную</span>
                    {m.title} <span className="muted">({m.page_count} л.)</span>
                  </span>
                  <button className="ghost danger" onClick={() => setManual(manual.filter((_, j) => j !== i))}>✕</button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {loading ? <p className="muted">Загрузка...</p> : (
          <>
            <div className="row" style={{ justifyContent: 'space-between', marginBottom: 8 }}>
              <span className="muted">Показано {items.length} из {total}</span>
              <button className="ghost" onClick={selectAllOnPage}>Выбрать все свободные на странице</button>
            </div>

            <table>
              <thead>
                <tr>
                  <th style={{width: 32}}></th>
                  <th style={{width: 90}}>Дата рег.</th>
                  <th style={{width: 110}}>Вх. №</th>
                  <th style={{width: 110}}>Исх. №</th>
                  <th>Документ</th>
                  <th style={{width: 80}}>№ док.</th>
                  <th style={{width: 70}}>Шифр</th>
                  <th style={{width: 150}}>Орган</th>
                  <th style={{width: 70}}>Сотрудник</th>
                  <th style={{width: 150}}>Дело</th>
                </tr>
              </thead>
              <tbody>
                {items.map(c => {
                  const isPlaced = !!c.placed
                  const checked = isSelected(c.external_ref)
                  return (
                    <tr key={c.external_ref} className={isPlaced ? 'row-disabled' : ''}>
                      <td><input type="checkbox" disabled={isPlaced} checked={checked} onChange={() => toggle(c)} /></td>
                      <td className="muted" style={{fontSize: 11}}>{c.incoming_date ? new Date(c.incoming_date).toLocaleDateString('ru-RU') : '—'}</td>
                      <td className="muted" style={{fontSize: 11}}>{c.incoming_num || '—'}</td>
                      <td className="muted" style={{fontSize: 11}}>{c.outgoing_num || '—'}</td>
                      <td>{c.title}</td>
                      <td className="muted" style={{fontSize: 11}}>{c.doc_num || '—'}</td>
                      <td className="muted" style={{fontSize: 11}}>{c.cipher || '—'}</td>
                      <td style={{fontSize: 11}}>{c.organ || '—'}</td>
                      <td className="muted" style={{fontSize: 11}}>{c.employee || '—'}</td>
                      <td>
                        {isPlaced ? (
                          <span className="conflict-note" style={{fontSize: 11}}>
                            д. {c.placed.delo} - {c.placed.year} т. {c.placed.tom} л. {c.placed.pages}
                            {!c.placed.own && ` (${c.placed.department})`}
                          </span>
                        ) : (
                          <span className="muted">свободен</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>

            {hasMore && (
              <div style={{ textAlign: 'center', marginTop: 12 }}>
                <button onClick={loadMore} disabled={loadingMore}>
                  {loadingMore ? 'Загрузка...' : `Показать ещё ${PAGE_SIZE}`}
                </button>
              </div>
            )}
          </>
        )}
      </Modal>

      {showManualModal && (
        <ManualAddModal onAdd={(m) => setManual([...manual, m])} onClose={() => setShowManualModal(false)} />
      )}
    </>
  )
}

function ManualAddModal({ onAdd, onClose }) {
  const [title, setTitle] = useState('')
  const [acc, setAcc] = useState('')
  const [pages, setPages] = useState(1)
  const [types, setTypes] = useState([])
  const [saveAsTemplate, setSaveAsTemplate] = useState(false)
  const [busy, setBusy] = useState(false)

  useEffect(() => { api.listDocumentTypes().then(setTypes).catch(() => {}) }, [])

  const save = async () => {
    if (!title || pages <= 0 || pages > 250) return
    setBusy(true)
    try {
      if (saveAsTemplate && !types.find(t => t.name === title)) await api.createDocumentType(title)
      onAdd({ source: 'manual', title, account_number: acc || null, page_count: pages })
      onClose()
    } catch (err) { alert(err.message) } finally { setBusy(false) }
  }

  return (
    <Modal title="Новый документ" onClose={onClose} footer={<><button onClick={onClose} disabled={busy}>Отмена</button><button className="primary" onClick={save} disabled={busy || !title || pages < 1}>Добавить</button></>}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <label><div className="muted" style={{ marginBottom: 4 }}>Название</div><input list="manual-doc-templates" placeholder="Выберите шаблон или введите текст" value={title} onChange={e => setTitle(e.target.value)} style={{ width: '100%' }} autoFocus /><datalist id="manual-doc-templates">{types.map(t => <option key={t.id} value={t.name} />)}</datalist></label>
        <label><div className="muted" style={{ marginBottom: 4 }}>Учётный №</div><input placeholder="Например, СЧ-218" value={acc} onChange={e => setAcc(e.target.value)} style={{ width: '100%' }} /></label>
        <label><div className="muted" style={{ marginBottom: 4 }}>Листов (1–250)</div><input type="number" min={1} max={250} value={pages} onChange={e => setPages(parseInt(e.target.value) || 1)} style={{ width: 120 }} /></label>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, cursor: 'pointer' }}><input type="checkbox" checked={saveAsTemplate} onChange={e => setSaveAsTemplate(e.target.checked)} /> Сохранить название в шаблоны</label>
      </div>
    </Modal>
  )
}

function DraftEditorModal({ preview, deloId, onRefresh, onClose, onCommit, onError }) {
  const [busy, setBusy] = useState(false)
  const [draggedIdx, setDraggedIdx] = useState(null)
  const [dragOverIdx, setDragOverIdx] = useState(null)
  const [localError, setLocalError] = useState('')
  const [showManualModal, setShowManualModal] = useState(false)

  const overflowInfo = {}
  for (let i = 0; i < preview.plan.length - 1; i++) {
    const t = preview.plan[i]
    if (t.final_page < t.max_pages) {
      const nextTom = preview.plan[i + 1]
      if (nextTom && nextTom.items && nextTom.items.length > 0) {
        const firstDoc = nextTom.items[0]
        overflowInfo[firstDoc.id] = { missing: t.max_pages - t.final_page, tomNumber: t.tom_number }
      }
    }
  }

  const patch = async (itemId, data) => {
    setBusy(true)
    try { await api.patchDraftItem(deloId, itemId, data); await onRefresh() } catch (err) { setLocalError(err.message) } finally { setBusy(false) }
  }

  const remove = async (itemId) => {
    setBusy(true)
    try { await api.deleteDraftItem(deloId, itemId); await onRefresh() } catch (err) { setLocalError(err.message) } finally { setBusy(false) }
  }

  const handleDrop = async (from, to) => {
    const arr = [...preview.items]; const [moved] = arr.splice(from, 1); arr.splice(to, 0, moved)
    setBusy(true)
    try { await api.reorderDraftItems(deloId, arr.map(it => it.id)); await onRefresh() } catch (err) { setLocalError(err.message) } finally { setBusy(false) }
  }

  const addManual = async (m) => {
    setBusy(true)
    try {
      const current = preview.items.map(it => ({ source: it.source, external_ref: it.external_ref, title: it.title, account_number: it.account_number, page_count: it.page_count, type_id: it.type_id }))
      await api.setDraftItems(deloId, [...current, m]); await onRefresh(); setShowManualModal(false)
    } catch (err) { setLocalError(err.message) } finally { setBusy(false) }
  }

  const clear = async () => {
    if (!confirm('Очистить черновик?')) return
    setBusy(true)
    try { await api.setDraftItems(deloId, []); await onRefresh(); onClose() } catch (err) { setLocalError(err.message) } finally { setBusy(false) }
  }

  const commit = async () => {
    setBusy(true); setLocalError('')
    try {
      const res = await onCommit()
      const rawName = preview.delo.full_title.replace('Дело № ', ''); const deloName = rawName.replace('-', ' - ')
      alert(`В дело ${deloName} добавлено ${preview.items.length} док. на ${preview.total_pages} л.`)
    } catch (err) {
      const detail = err.body?.detail
      let msg = ''
      if (detail?.conflicts && detail.conflicts.length > 0) msg = 'Документы уже размещены:\n' + detail.conflicts.map(c => `• «${c.title || c.external_ref}» — ${c.location}`).join('\n')
      else if (detail?.violations && detail.violations.length > 0) msg = 'Нарушения:\n' + detail.violations.map(v => `• ${v.message}`).join('\n')
      else if (typeof detail === 'string') msg = detail
      else if (detail?.message) msg = detail.message
      else msg = err.message
      setLocalError(msg)
    } finally { setBusy(false) }
  }

  return (
    <Modal title={`Черновик — ${preview.items.length} док., ${preview.total_pages} л.`} onClose={onClose} wide headerRight={<button className="ghost" onClick={() => setShowManualModal(true)} disabled={busy}>+ Добавить вручную</button>} footer={<><button className="ghost danger" onClick={clear} disabled={busy}>Очистить</button><button onClick={onClose}>Отмена</button><button className="primary" onClick={commit} disabled={busy || !preview.can_commit}>Зафиксировать</button></>}>
      {localError && <div className="error" style={{ whiteSpace: 'pre-line', marginBottom: 12 }}>⚠ {localError}</div>}
      {preview.conflicts.length > 0 && !localError && <div className="error" style={{ marginBottom: 12 }}><b>Документы уже размещены:</b>{preview.conflicts.map((c, i) => <div key={i}>⚠ «{c.title || c.external_ref}» — {c.location}</div>)}<div className="muted" style={{ marginTop: 6, fontSize: 12 }}>Удалите их из черновика (кнопка ✕).</div></div>}

      <table>
        <thead>
          <tr>
            <th style={{width: 32}}></th>
            <th style={{width: 40}}>№</th>
            <th style={{width: 140}}>Вх. №</th>
            <th style={{width: 140}}>Исх. №</th>
            <th style={{width: 40}}>Экз.</th>
            <th>Документ</th>
            <th style={{width: 80}}>Листов</th>
            <th style={{width: 50}}></th>
          </tr>
        </thead>
        <tbody>
          {preview.items.map((it, idx) => {
            const overflow = overflowInfo[it.id]
            const incStr = it.incoming_num ? `${it.incoming_num} от ${it.incoming_date ? new Date(it.incoming_date).toLocaleDateString('ru-RU') : '—'}` : ''
            const outStr = it.outgoing_num ? `${it.outgoing_num} от ${it.outgoing_date ? new Date(it.outgoing_date).toLocaleDateString('ru-RU') : '—'}` : ''
            return (
              <tr key={it.id} draggable={!busy} onDragStart={(e) => { if (e.target.tagName === 'INPUT' || e.target.tagName === 'BUTTON') { e.preventDefault(); return; } setDraggedIdx(idx); e.dataTransfer.effectAllowed = 'move'; }} onDragOver={(e) => { e.preventDefault(); if (draggedIdx !== null && draggedIdx !== idx) setDragOverIdx(idx); }} onDragLeave={() => setDragOverIdx(null)} onDrop={(e) => { e.preventDefault(); if (draggedIdx !== null && draggedIdx !== idx) handleDrop(draggedIdx, idx); setDraggedIdx(null); setDragOverIdx(null); }} onDragEnd={() => { setDraggedIdx(null); setDragOverIdx(null); }} style={{ opacity: draggedIdx === idx ? 0.3 : 1, backgroundColor: dragOverIdx === idx ? '#e8efff' : overflow ? '#fdf3f3' : 'transparent', cursor: 'grab' }}>
                <td className="muted" style={{ textAlign: 'center', fontSize: 18 }}>≡</td>
                <td className="cell-num">{idx + 1}</td>
                <td style={{fontSize: 12}}>{incStr}</td>
                <td style={{fontSize: 12}}>{outStr}</td>
                <td style={{textAlign: 'center'}}>{it.copy_num || '1'}</td>
                <td>
                  <div style={{display: 'flex', flexWrap: 'wrap', gap: 4, alignItems: 'center'}}>
                    <input defaultValue={it.title} onBlur={e => e.target.value !== it.title && patch(it.id, {title: e.target.value})} style={{width: '150px'}} disabled={busy} />
                    <input defaultValue={it.doc_num || ''} onBlur={e => e.target.value !== (it.doc_num || '') && patch(it.id, {doc_num: e.target.value})} style={{width: '70px'}} placeholder="№ док." disabled={busy} />
                    <input defaultValue={it.organ || ''} onBlur={e => e.target.value !== (it.organ || '') && patch(it.id, {organ: e.target.value})} style={{width: '130px'}} placeholder="Орган" disabled={busy} />
                  </div>
                  {overflow && <div style={{ fontSize: 11, color: '#d64545', marginTop: 4 }}>⚠ Не помещается в том {overflow.tomNumber} (не хватает {overflow.missing} л.). Уменьшите листы или удалите.</div>}
                </td>
                <td><input type="number" min={1} max={250} defaultValue={it.page_count} onBlur={e => parseInt(e.target.value) !== it.page_count && patch(it.id, {page_count: parseInt(e.target.value)})} style={{width: 60, borderColor: overflow ? '#f0c0c0' : undefined}} disabled={busy} /></td>
                <td><button className="ghost danger" onClick={() => remove(it.id)} disabled={busy}>✕</button></td>
              </tr>
            )
          })}
        </tbody>
      </table>

      <h3 style={{marginTop: 20}}>План разбиения</h3>
      {preview.plan.length === 0 && <p className="muted">—</p>}
      {preview.plan.map((p, i) => {
        const invalid = !p.is_last && p.final_page !== p.max_pages; const full = p.final_page === p.max_pages; const pct = Math.round((p.final_page / p.max_pages) * 100)
        return (
          <div key={i} className={`plan-tom ${full ? 'full' : ''} ${invalid ? 'invalid' : ''}`}>
            <div className="plan-tom-head"><span className="plan-tom-title">Том {p.tom_number}{!p.existing && <span className="badge new">новый</span>}{p.is_last && <span className="badge last">последний</span>}</span><span className="plan-tom-pages">{p.final_page} / {p.max_pages} л.</span></div>
            <div className="progress"><div className={`progress-bar ${full ? 'full' : ''}`} style={{width: `${pct}%`}} /></div>
            {invalid && <div className="plan-tom-warn">❌ Не хватает {p.max_pages - p.final_page} л. Промежуточный том должен быть ровно {p.max_pages}</div>}
          </div>
        )
      })}
      {preview.violations.length > 0 && <div className="error" style={{ marginTop: 12 }}>{preview.violations.map((v, i) => <div key={i}>⚠ {v.message}</div>)}</div>}
      {showManualModal && <ManualAddModal onAdd={addManual} onClose={() => setShowManualModal(false)} />}
    </Modal>
  )
}

function TomModal({ tomId, deloClosed, isAdmin, onClose, onUpdate, onError }) {
  const [tom, setTom] = useState(null)
  const [busy, setBusy] = useState(false)
  const [draggedIdx, setDraggedIdx] = useState(null)
  const [dragOverIdx, setDragOverIdx] = useState(null)
  const [localError, setLocalError] = useState('')

  const load = () => api.tomDetail(tomId).then(setTom).catch(e => setLocalError(e.message))
  useEffect(() => { load() }, [tomId])

  const update = async (docId, data) => {
    setBusy(true); setLocalError('')
    try {
      await api.updateDocument(docId, data)
      await load()
      onUpdate && onUpdate()
    } catch (err) {
      setLocalError(err.message)
      await load() // откатываем ввод к актуальному состоянию БД
    } finally { setBusy(false) }
  }

  const remove = async (docId) => {
    if (!confirm('Удалить документ?')) return
    setBusy(true); setLocalError('')
    try { await api.deleteDocument(docId); await load(); onUpdate && onUpdate() } catch (err) { setLocalError(err.message) } finally { setBusy(false) }
  }

  const handleDrop = async (from, to) => {
    const arr = [...tom.documents]; const [moved] = arr.splice(from, 1); arr.splice(to, 0, moved)
    setBusy(true); setLocalError('')
    try { await api.reorderTomDocuments(tomId, arr.map(d => d.id)); await load(); onUpdate && onUpdate() } catch (err) { setLocalError(err.message) } finally { setBusy(false) }
  }

  const downloadExcel = () => { window.location.href = `/api/toms/${tomId}/export`; }
  const editable = !isAdmin && !deloClosed && tom?.tom?.status === 'open'

  return (
    <Modal
      title={tom ? `Том ${tom.tom.tom_number} — ${tom.tom.current_end}/${tom.tom.max_pages} л.` : 'Загрузка...'}
      onClose={onClose}
      wide
      headerRight={
        <button className="ghost" onClick={downloadExcel} style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600 }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: '#217346' }}>
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="8" y1="13" x2="16" y2="13"></line>
            <line x1="8" y1="17" x2="16" y2="17"></line>
            <polyline points="10 9 9 9 8 9"></polyline>
          </svg>
          Скачать Excel
        </button>
      }
      footer={
        <>
          {localError ? (
            <div className="error" style={{ margin: 0, padding: '8px 12px', fontSize: 12, marginRight: 'auto', maxWidth: '75%', whiteSpace: 'pre-line', maxHeight: 60, overflowY: 'auto' }}>
              ⚠ {localError}
            </div>
          ) : (
            <span style={{ marginRight: 'auto' }}></span>
          )}
          <button onClick={onClose}>Закрыть</button>
        </>
      }
    >
      {!tom ? <p className="muted">Загрузка...</p> :
        tom.documents.length === 0 ? <p className="muted">Документов нет</p> : (
          <table>
            <thead>
              <tr>
                {editable && <th style={{width: 32}}></th>}
                <th style={{width: 40}}>№</th>
                <th style={{width: 140}}>Вх. №</th>
                <th style={{width: 140}}>Исх. №</th>
                <th style={{width: 40}}>Экз.</th>
                <th>Документ</th>
                {editable && <th style={{width: 80}}>Листов</th>}
                <th style={{width: 100}}>Страницы</th>
                {editable && <th style={{width: 50}}></th>}
              </tr>
            </thead>
            <tbody>
              {tom.documents.map((d, idx) => {
                const incStr = d.incoming_num ? `${d.incoming_num} от ${d.incoming_date ? new Date(d.incoming_date).toLocaleDateString('ru-RU') : '—'}` : ''
                const outStr = d.outgoing_num ? `${d.outgoing_num} от ${d.outgoing_date ? new Date(d.outgoing_date).toLocaleDateString('ru-RU') : '—'}` : ''
                const isChanged = d.title !== d.original_title || d.doc_num !== d.original_doc_num || d.organ !== d.original_organ || d.page_count !== d.original_page_count
                
                return (
                  <tr key={d.id} draggable={editable && !busy} onDragStart={(e) => { if (e.target.tagName === 'INPUT' || e.target.tagName === 'BUTTON') { e.preventDefault(); return; } setDraggedIdx(idx); e.dataTransfer.effectAllowed = 'move'; }} onDragOver={(e) => { e.preventDefault(); if (draggedIdx !== null && draggedIdx !== idx) setDragOverIdx(idx); }} onDragLeave={() => setDragOverIdx(null)} onDrop={(e) => { e.preventDefault(); if (draggedIdx !== null && draggedIdx !== idx) handleDrop(draggedIdx, idx); setDraggedIdx(null); setDragOverIdx(null); }} onDragEnd={() => { setDraggedIdx(null); setDragOverIdx(null); }} style={{ opacity: draggedIdx === idx ? 0.3 : 1, backgroundColor: dragOverIdx === idx ? '#e8efff' : undefined, cursor: editable ? 'grab' : 'default' }}>
                    {editable && <td className="muted" style={{ textAlign: 'center', fontSize: 18 }}>≡</td>}
                    <td className="cell-num">{d.order_in_tom}</td>
                    <td style={{fontSize: 12}}>{incStr}</td>
                    <td style={{fontSize: 12}}>{outStr}</td>
                    <td style={{textAlign: 'center'}}>{d.copy_num || '1'}</td>
                    <td>
                      {editable ? (
                        <div style={{display: 'flex', flexWrap: 'wrap', gap: 4, alignItems: 'center'}}>
                          <input defaultValue={d.title} onBlur={e => e.target.value !== d.title && update(d.id, {title: e.target.value})} style={{width: '150px'}} />
                          <input defaultValue={d.doc_num || ''} onBlur={e => e.target.value !== (d.doc_num || '') && update(d.id, {doc_num: e.target.value})} style={{width: '70px'}} placeholder="№ док." />
                          <input defaultValue={d.organ || ''} onBlur={e => e.target.value !== (d.organ || '') && update(d.id, {organ: e.target.value})} style={{width: '130px'}} placeholder="Орган" />
                        </div>
                      ) : (
                        <div style={{display: 'flex', flexWrap: 'wrap', gap: 4, alignItems: 'center'}}>
                          <span>{docLabel(d.title, d.doc_num, d.organ)}</span>
                          {isChanged && <span className="badge" style={{ backgroundColor: '#fff3cd', color: '#856404', fontSize: 10 }}>Изменено</span>}
                        </div>
                      )}
                      {isChanged && d.changes && d.changes.length > 0 && (
                        <details style={{ marginTop: 6, fontSize: 11, color: '#666' }}>
                          <summary style={{ cursor: 'pointer', color: '#3b6fd6', padding: 0 }}>Показать историю</summary>
                          <div style={{ backgroundColor: '#f8f9fa', padding: 8, borderRadius: 4, marginTop: 4, border: '1px solid #eee' }}>
                            {d.changes.map((c, i) => (
                              <div key={i} style={{ marginBottom: 4 }}>
                                <b>{c.field}:</b> "{c.old}" → "{c.new}" 
                                <span className="muted"> ({c.user}, {new Date(c.date).toLocaleDateString('ru-RU')})</span>
                              </div>
                            ))}
                          </div>
                        </details>
                      )}
                    </td>
                    {editable && (
                      <td>
                        <input type="number" min={1} max={250} defaultValue={d.page_count} onBlur={e => { const val = parseInt(e.target.value); if (val !== d.page_count) update(d.id, {page_count: val}) }} style={{width: 60}} />
                      </td>
                    )}
                    <td>
                      <span style={{fontSize: 13, color: 'var(--text-muted)'}}>{formatPages(d.page_start, d.page_end)}</span>
                    </td>
                    {editable && <td><button className="ghost danger" onClick={() => remove(d.id)} disabled={busy}>✕</button></td>}
                  </tr>
                )
              })}
            </tbody>
          </table>
        )
      }
    </Modal>
  )
}

export default function DeloDetail({ user }) {
  const { id } = useParams()
  const isAdmin = user?.role === 'admin'
  const [preview, setPreview] = useState(null)
  const [toms, setToms] = useState([])
  const [error, setError] = useState('')
  const [modal, setModal] = useState(null)
  const [activeTom, setActiveTom] = useState(null)
  const [showMenu, setShowMenu] = useState(false)
  const menuRef = useRef(null)

  const reload = async () => { try { const [p, t] = await Promise.all([api.getDraft(id), api.listToms(id)]); setPreview(p); setToms(t) } catch (err) { setError(err.message) } }
  useEffect(() => { reload() }, [id])
  useEffect(() => { if (!showMenu) return; const handler = (e) => { if (menuRef.current && !menuRef.current.contains(e.target)) setShowMenu(false); }; document.addEventListener('mousedown', handler); return () => document.removeEventListener('mousedown', handler) }, [showMenu])

  const handleSaveSelection = async (items) => { await api.setDraftItems(id, items); await reload(); setModal('editor') }
  const handleCommit = async () => { const res = await api.commitDraft(id); await reload(); setModal(null); return res }
  const handleCloseDelo = async () => {
    if (!confirm('Завершить дело? После этого редактирование станет невозможным.')) return
    try { await api.closeDelo(id); await reload() } catch (err) {
      const detail = err.body?.detail
      if (detail?.error === 'intermediate_toms_not_full') setError('Нельзя закрыть дело: промежуточные томы не заполнены до 250: ' + detail.violations.map(v => `том ${v.tom_number} — ${v.filled}/${v.filled + v.missing}`).join(', '))
      else setError(err.message)
    }
  }

  if (!preview) return <div className="container"><p className="muted">Загрузка...</p></div>
  const draftEmpty = preview.items.length === 0; const isDeloClosed = preview.delo.status === 'closed'; const readOnly = isAdmin || isDeloClosed

  return (
    <div>
      <div className="breadcrumb"><Link to="/">← К делам</Link></div>
      <div className="page-head">
        <h1 className="page-title">{preview.delo.full_title}{isAdmin && preview.delo.department_name && <span className="badge dept-badge">{preview.delo.department_name}</span>}</h1>
        <div className="page-head-actions">
          {isDeloClosed && <StatusBadge status="closed" />}
          {isAdmin && <span className="pill">Просмотр</span>}
          {!readOnly && (
            <>
              {!draftEmpty ? <button className="primary" onClick={() => setModal('editor')}>Продолжить черновик ({preview.items.length})</button> : <button className="primary" onClick={() => setModal('select')}>+ Выбрать документы</button>}
              <div className="dropdown-wrap" ref={menuRef}>
                <button className="ghost dropdown-trigger" onClick={() => setShowMenu(v => !v)} title="Ещё">⋮ Ещё</button>
                {showMenu && <div className="dropdown-menu">{toms.length > 0 ? <button className="dropdown-item danger" onClick={() => { setShowMenu(false); handleCloseDelo() }}>⚠ Завершить дело</button> : <div className="dropdown-empty">Нет доступных действий</div>}</div>}
              </div>
            </>
          )}
        </div>
      </div>

      {error && <div className="error" style={{whiteSpace: 'pre-line'}}>⚠ {error}</div>}
      {!isAdmin && !isDeloClosed && preview.other_drafts && preview.other_drafts.length > 0 && (
        <div className="card" style={{ padding: '10px 18px', marginBottom: 12, background: '#fff8e1', borderColor: '#f0d68a' }}>
          <span className="muted">⚡ Также работают с этим делом: </span>{preview.other_drafts.map((od, i) => <span key={i} className="badge manual-badge" style={{ marginLeft: 6 }}>{od.user_login} · {od.items_count} док.</span>)}
        </div>
      )}

      <div className="stats-bar">
        <div className="stat"><div className="stat-label">{isDeloClosed ? 'Финальный том' : 'Текущий том'}</div><div className="stat-value">{preview.current_tom.id ? `№ ${preview.current_tom.tom_number}` : '—'}</div><div className="stat-sub">{preview.current_tom.id ? `${preview.current_tom.current_end} / ${preview.current_tom.max_pages} л.` : 'ещё не создан'}</div></div>
        <div className="stat"><div className="stat-label">Всего томов</div><div className="stat-value">{toms.length}</div></div>
        {!isAdmin && !isDeloClosed && <div className="stat"><div className="stat-label">В черновике</div><div className="stat-value">{preview.items.length}</div><div className="stat-sub">{preview.total_pages} л.</div></div>}
      </div>

      <div className="card">
        <div className="card-head"><h3>Тома дела</h3><span className="muted">всего: {toms.length}</span></div>
        {toms.length === 0 && <p className="muted">Томов ещё нет</p>}
        <div className="toms-grid">
          {toms.map(t => {
            const full = t.current_end === t.max_pages; const pct = t.max_pages ? Math.round((t.current_end / t.max_pages) * 100) : 0
            return (
              <div key={t.id} className={`tom-card ${full ? 'full' : ''}`}>
                <div className="tom-card-head"><span className="tom-card-title">Том {t.tom_number}</span><StatusBadge status={t.status} /></div>
                <div className="tom-card-meta">{t.current_end} / {t.max_pages} л. · {t.documents_count} док.</div>
                <div className="progress"><div className={`progress-bar ${full ? 'full' : ''}`} style={{width: `${pct}%`}} /></div>
                <button className="ghost" style={{marginTop: 8}} onClick={() => { setActiveTom(t.id); setModal('tom') }}>Открыть →</button>
              </div>
            )
          })}
        </div>
      </div>

      {modal === 'select' && <SelectDocumentsModal deloId={id} currentTom={preview.current_tom} onSave={handleSaveSelection} onClose={() => setModal(null)} onError={setError} />}
      {modal === 'editor' && <DraftEditorModal preview={preview} deloId={id} onRefresh={reload} onClose={() => setModal(null)} onCommit={handleCommit} onError={setError} />}
      {modal === 'tom' && activeTom && <TomModal tomId={activeTom} deloClosed={isDeloClosed} isAdmin={isAdmin} onClose={() => { setModal(null); setActiveTom(null) }} onUpdate={reload} onError={setError} />}
    </div>
  )
}
