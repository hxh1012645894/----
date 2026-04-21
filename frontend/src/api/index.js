import { API_HOST, API_PORT } from './config'

const BASE_URL = `http://${API_HOST}:${API_PORT}`

/**
 * 后端 API 地址配置
 */
export const API = {
  // 审核相关
  audit: `${BASE_URL}/api/audit`,

  // 报告相关
  reports: `${BASE_URL}/api/reports`,
  saveReport: `${BASE_URL}/api/reports/save`,
  exportWord: (id) => `${BASE_URL}/api/reports/export/word/${id}`,
  exportPdf: (id) => `${BASE_URL}/api/reports/export/pdf/${id}`,

  // 管理相关
  admin: {
    prompts: `${BASE_URL}/api/admin/prompts`,
    promptsDetail: (key) => `${BASE_URL}/api/admin/prompts/${key}`,
    improvePrompt: `${BASE_URL}/api/admin/prompts/improve`,
    dictionary: `${BASE_URL}/api/admin/dictionary`,
  },
}

/**
 * 上传文件预览地址
 */
export const UPLOAD_URL = (filename) => `${BASE_URL}/uploads/${encodeURIComponent(filename)}`
