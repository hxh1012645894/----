// 管理后台相关 API

// 获取提示词列表
export async function fetchPrompts() {
  const res = await fetch('/api/admin/prompts')
  return res.json()
}

// 保存单个提示词
export async function savePrompt(promptKey, content) {
  const res = await fetch(`/api/admin/prompts/${promptKey}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content })
  })
  return res.ok
}

// AI 优化提示词
export async function aiImprovePrompt(currentPrompt, issuesFeedback) {
  const res = await fetch('/api/admin/prompts/improve', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      current_prompt: currentPrompt,
      issues_feedback: issuesFeedback
    })
  })
  return res.json()
}

// 获取匹配字典
export async function fetchDictionary() {
  const res = await fetch('/api/admin/dictionary')
  return res.json()
}

// 保存匹配字典
export async function saveDictionary(parsedData) {
  const res = await fetch('/api/admin/dictionary', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(parsedData)
  })
  return res.ok
}