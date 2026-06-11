import request from './request'

export const getMenuTree = () => request.get('/api/menu/tree')
export const getMenuList = () => request.get('/api/menu/list')
