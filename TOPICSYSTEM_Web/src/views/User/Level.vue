<template>
  <div class="page-container">
    <div class="page-header">
      <h2>用户等级</h2>
    </div>
    <el-table :data="[]" border style="width: 100%">
      <el-table-column prop="level" label="等级" width="100" />
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="minExp" label="最低经验" width="120" />
      <el-table-column prop="maxExp" label="最高经验" width="120" />
      <el-table-column label="操作" width="200">
        <template #default>
          <el-button type="primary" size="small">编辑</el-button>
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
