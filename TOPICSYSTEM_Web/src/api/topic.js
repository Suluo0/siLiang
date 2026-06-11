import request from './request'

export const getTopicList = (params) => request.get('/v1/topic/list', { params })

export const getTopicDetail = (topicId) => request.get(`/v1/topic/${topicId}`)

export const getTopicTags = () => request.get('/v1/topic/tags')
