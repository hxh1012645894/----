// 报告相关 API

// 获取报告列表（分页）
export async function fetchReports(page = 1, pageSize = 10) {
  const res = await fetch(`/api/reports?page=${page}&page_size=${pageSize}`)
  return res.json()
}

// 删除报告
export async function deleteReport(id) {
  const res = await fetch(`/api/reports/${id}`, { method: 'DELETE' })
  return res.ok
}

// 导出 Word
export function exportWord(id) {
  window.open(`/api/reports/export/word/${id}`, '_blank')
}

// 导出 PDF
export function exportPDF(id) {
  window.open(`/api/reports/export/pdf/${id}`, '_blank')
}