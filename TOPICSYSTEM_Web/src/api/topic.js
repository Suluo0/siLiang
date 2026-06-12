import request from './request'

export const getTopicList = (params) => request.get('/topic/list', { params })

export const getTopicDetail = (topicId) => request.get(`/topic/${topicId}`)

export const getTopicTags = () => request.get('/topic/tags')
