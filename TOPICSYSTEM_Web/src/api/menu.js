import request from './request'

export const getMenuTree = () => request.get('/menu/tree')
export const getMenuList = () => request.get('/menu/list')
