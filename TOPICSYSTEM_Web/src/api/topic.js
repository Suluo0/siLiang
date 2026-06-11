import request from './request'

export const getTopicList = (params) => {
  return request.get('/api/v1/topic/list', { params })
}

export const getTopicDetail = (topicId) => {
  return request.get(`/api/v1/topic/${topicId}`)
}