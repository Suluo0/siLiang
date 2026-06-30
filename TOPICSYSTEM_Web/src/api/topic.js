import request from './request'

export const getTopicList = (params) => request.get('/topic/list', { params })

export const getTopicDetail = (topicId) => request.get(`/topic/${topicId}`)

export const getTopicTags = () => request.get('/topic/tags')

// ── 掌握度 ──
// 仪表盘统计:已掌握 / 学习中 / 总题数
export const getDashboardStats = () => request.get('/topic/dashboard/stats')

// 手动标记掌握状态(旁路):status = 'mastered' | 'learning'
export const setTopicStatus = (topicId, status) =>
  request.post(`/topic/${topicId}/status`, { status })

// 掌握度自查:提交作答,返回五维评分 + 总分 + 是否达标 + feedback
export const masteryCheck = (topicId, answer) =>
  request.post(`/topic/${topicId}/mastery-check`, { answer })

// 历史自查记录(五维分 + 总分 + 时间),按时间倒序
export const getMasteryAttempts = (topicId) =>
  request.get(`/topic/${topicId}/attempts`)
