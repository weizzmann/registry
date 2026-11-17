const BASE = '/api'

async function request(path, opts = {}) {
  const res = await fetch(BASE + path, {
    ...opts,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(opts.headers || {}),
    },
  })
  if (!res.ok) {
    let body = {}
    try { body = await res.json() } catch {}
    
    // FastAPI кладёт текст ошибки в body.detail (строка) или
    // в body.detail.message (если HTTPException передан словарём)
    let message = `HTTP ${res.status}`
    if (typeof body.detail === 'string') {
      message = body.detail
    } else if (body.detail && typeof body.detail === 'object' && body.detail.message) {
      message = body.detail.message
    } else if (body.message) {
      message = body.message
    }

    const err = new Error(message)
    err.status = res.status
    err.body = body
    throw err
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  // ===== Авторизация и пользователи =====
  login: (login, password) =>
    request('/auth/login', { method: 'POST', body: JSON.stringify({ login, password }) }),
  logout: () => request('/auth/logout', { method: 'POST' }),
  me: () => request('/auth/me'),
  requestAccess: (data) =>
    request('/auth/request', { method: 'POST', body: JSON.stringify(data) }),
  publicDepartments: () => request('/auth/departments'),

  // ===== Дела =====
  listDelos: () => request('/delos'),
  createDelo: (data) =>
    request('/delos', { method: 'POST', body: JSON.stringify(data) }),
  listToms: (deloId) => request(`/delos/${deloId}/toms`),
  closeDelo: (deloId) =>
    request(`/delos/${deloId}/close`, { method: 'POST' }),

  // ===== Внешние документы (Стейджинг) =====
  listExternal: (params = {}) => {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== '') {
        q.append(k, v);
      }
    }
    return request('/external/documents' + (q.toString() ? '?' + q.toString() : ''));
  },
  syncExternal: () => request('/external/sync', { method: 'POST' }),
  adminSyncExternal: () => request('/admin/sync-external', { method: 'POST' }),

  // ===== Черновик =====
  getDraft: (deloId) => request(`/drafts/${deloId}`),
  setDraftItems: (deloId, items) =>
    request(`/drafts/${deloId}/items`, {
      method: 'POST', body: JSON.stringify({ items }),
    }),
  patchDraftItem: (deloId, itemId, data) =>
    request(`/drafts/${deloId}/items/${itemId}`, {
      method: 'PATCH', body: JSON.stringify(data),
    }),
  deleteDraftItem: (deloId, itemId) =>
    request(`/drafts/${deloId}/items/${itemId}`, { method: 'DELETE' }),
  reorderDraftItems: (deloId, order) =>
    request(`/drafts/${deloId}/reorder`, {
      method: 'POST', body: JSON.stringify({ order }),
    }),
  commitDraft: (deloId) =>
    request(`/drafts/${deloId}/commit`, { method: 'POST' }),

  // ===== Тома (просмотр и экспорт) =====
  tomDetail: (tomId) => request(`/toms/${tomId}`),
  reorderTomDocuments: (tomId, order) =>
    request(`/toms/${tomId}/reorder`, {
      method: 'POST', body: JSON.stringify({ order }),
    }),

  // ===== Документы (в томе) =====
  updateDocument: (docId, data) =>
    request(`/documents/${docId}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteDocument: (docId) =>
    request(`/documents/${docId}`, { method: 'DELETE' }),

  // ===== Глобальный поиск =====
  searchDocuments: (q, limit = 50, offset = 0) => {
    const params = new URLSearchParams({
      q,
      limit: String(limit),
      offset: String(offset),
    })
    return request('/documents/search?' + params.toString())
  },

  // ===== Справочник типов =====
  listDocumentTypes: () => request('/documents/types'),
  createDocumentType: (name) =>
    request('/documents/types', { method: 'POST', body: JSON.stringify({ name }) }),

  // ===== Администрирование =====
  adminRequests: () => request('/admin/requests'),
  approveRequest: (id, data) =>
    request(`/admin/requests/${id}/approve`, {
      method: 'POST', body: JSON.stringify(data),
    }),
  rejectRequest: (id) =>
    request(`/admin/requests/${id}/reject`, { method: 'POST' }),
  
  adminUsers: () => request('/admin/users'),
  adminDepartments: () => request('/admin/departments'),
  createDepartment: (data) =>
    request('/admin/departments', { method: 'POST', body: JSON.stringify(data) }),
  
  deactivateUser: (id) =>
    request(`/admin/users/${id}/deactivate`, { method: 'POST' }),
  resetUserPassword: (id) =>
    request(`/admin/users/${id}/reset-password`, { method: 'POST' }),
  changeUserDepartment: (id, departmentId) =>
    request(`/admin/users/${id}/department`, {
      method: 'PATCH',
      body: JSON.stringify({ department_id: departmentId }),
    }),
}