// 审核相关 API

// 提交审核 - 单文件逐个处理
export async function submitAuditSingle(formData) {
  const response = await fetch('/api/audit', {
    method: 'POST',
    body: formData
  })
  return response.json()
}

// 保存综合报告
export async function saveReport(batchName, totalCount, passCount, passRate, details) {
  const response = await fetch('/api/reports/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      batch_name: batchName,
      total_count: totalCount,
      pass_count: passCount,
      pass_rate: passRate,
      details: details
    })
  })
  return response.ok
}