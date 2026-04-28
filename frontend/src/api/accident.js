// 事故分析台账相关 API

// 获取事故类型列表
export async function fetchAccidentTypes() {
  const res = await fetch('/api/accidents/types')
  return res.json()
}

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