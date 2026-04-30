// 事故分析台账相关 API

// ==================== 事故类型管理 ====================

// 获取事故类型列表
export async function fetchAccidentTypes() {
  const res = await fetch('/api/accidents/types')
  return res.json()
}

// 新增事故类型
export async function createAccidentType(typeName) {
  const res = await fetch(`/api/accidents/types?type_name=${encodeURIComponent(typeName)}`, {
    method: 'POST'
  })
  return res.json()
}

// 更新事故类型
export async function updateAccidentType(id, typeName) {
  const res = await fetch(`/api/accidents/types/${id}?type_name=${encodeURIComponent(typeName)}`, {
    method: 'PUT'
  })
  return res.json()
}

// 删除事故类型
export async function deleteAccidentType(id) {
  const res = await fetch(`/api/accidents/types/${id}`, {
    method: 'DELETE'
  })
  return res.json()
}

// ==================== 基础事故操作 ====================

// 获取事故台账列表
export async function fetchAccidents() {
  const res = await fetch('/api/accidents')
  return res.json()
}

// 获取事故详情
export async function fetchAccidentDetail(id) {
  const res = await fetch(`/api/accidents/${id}`)
  return res.json()
}

// 创建事故记录
export async function createAccident(data) {
  const res = await fetch('/api/accidents', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  return res.json()
}

// 更新事故记录
export async function updateAccident(id, data) {
  const res = await fetch(`/api/accidents/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  return res.json()
}

// 删除事故记录
export async function deleteAccident(id) {
  const res = await fetch(`/api/accidents/${id}`, { method: 'DELETE' })
  return res.json()
}

// 提交事故并触发AI分析
export async function submitAccidentForAnalysis(id) {
  const res = await fetch(`/api/accidents/${id}/submit`, { method: 'POST' })
  return res.json()
}

// 上传附件
export async function uploadAccidentAttachments(files) {
  const formData = new FormData()
  files.forEach(file => formData.append('files', file))
  const res = await fetch('/api/accidents/upload', {
    method: 'POST',
    body: formData
  })
  return res.json()
}

// ==================== 整改措施 ====================

export async function fetchMeasures(accidentId) {
  const res = await fetch(`/api/accidents/${accidentId}/measures`)
  return res.json()
}

export async function addMeasure(accidentId, data) {
  const res = await fetch(`/api/accidents/${accidentId}/measures`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  return res.json()
}

export async function updateMeasure(accidentId, measureId, data) {
  const res = await fetch(`/api/accidents/${accidentId}/measures/${measureId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  return res.json()
}

export async function assignMeasure(accidentId, measureId, data) {
  const res = await fetch(`/api/accidents/${accidentId}/measures/${measureId}/assign`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  return res.json()
}

export async function completeMeasure(accidentId, measureId, data) {
  const res = await fetch(`/api/accidents/${accidentId}/measures/${measureId}/complete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  return res.json()
}

export async function updateMeasureStatus(accidentId, measureId, status) {
  const res = await fetch(`/api/accidents/${accidentId}/measures/${measureId}/status`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status })
  })
  return res.json()
}

export async function fetchOverdueMeasures() {
  const res = await fetch('/api/accidents/measures/overdue')
  return res.json()
}

export async function checkAndMarkOverdue() {
  const res = await fetch('/api/accidents/measures/check-overdue', {
    method: 'POST'
  })
  return res.json()
}

// ==================== 事故警示 ====================

export async function fetchAlert(accidentId) {
  const res = await fetch(`/api/accidents/${accidentId}/alert`)
  return res.json()
}

export async function generateAlert(accidentId) {
  const res = await fetch(`/api/accidents/${accidentId}/alert/generate`, {
    method: 'POST'
  })
  return res.json()
}

export async function updateAlert(accidentId, data) {
  const res = await fetch(`/api/accidents/${accidentId}/alert`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  return res.json()
}

export async function sendAlert(accidentId) {
  const res = await fetch(`/api/accidents/${accidentId}/alert/send`, {
    method: 'POST'
  })
  return res.json()
}

// ==================== 培训记录 ====================

export async function fetchTrainings(accidentId) {
  const res = await fetch(`/api/accidents/${accidentId}/trainings`)
  return res.json()
}

export async function addTraining(accidentId, data) {
  const res = await fetch(`/api/accidents/${accidentId}/trainings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  return res.json()
}

export async function updateTraining(accidentId, trainingId, data) {
  const res = await fetch(`/api/accidents/${accidentId}/trainings/${trainingId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  return res.json()
}

export async function deleteTraining(accidentId, trainingId) {
  const res = await fetch(`/api/accidents/${accidentId}/trainings/${trainingId}`, {
    method: 'DELETE'
  })
  return res.json()
}

// ==================== 台账导出与编辑 ====================

export async function generateLedger(accidentId) {
  const res = await fetch(`/api/accidents/${accidentId}/ledger/generate`, {
    method: 'POST'
  })
  return res.json()
}

export async function downloadLedger(accidentId) {
  const res = await fetch(`/api/accidents/${accidentId}/ledger/download`)
  return res.json()
}

export async function exportBatchLedger(accidentIds) {
  const res = await fetch('/api/accidents/ledger/export-batch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(accidentIds)
  })
  return res.json()
}

export async function fetchLedgerContent(accidentId) {
  const res = await fetch(`/api/accidents/${accidentId}/ledger/content`)
  return res.json()
}

export async function updateLedgerContent(accidentId, content) {
  const res = await fetch(`/api/accidents/${accidentId}/ledger/content`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(content)
  })
  return res.json()
}