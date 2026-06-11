<template>
  <div class="page-container">
    <div class="page-header">
      <h2>菜单管理</h2>
    </div>
    <el-table :data="[]" border style="width: 100%">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="菜单名称" />
      <el-table-column prop="path" label="路由路径" />
      <el-table-column prop="icon" label="图标" width="120" />
      <el-table-column label="操作" width="200">
        <template #default>
          <el-button type="primary" size="small">编辑</el-button>
          <el-button type="danger" size="small">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
</script>

<style scoped>
.page-container {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
}
.page-header {
  margin-bottom: 20px;
}
</style>
