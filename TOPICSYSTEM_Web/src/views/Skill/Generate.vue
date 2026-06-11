<template>
  <div class="page-container">
    <div class="page-header">
      <h2>技能生成</h2>
    </div>
    <el-card>
      <el-form label-width="120px">
        <el-form-item label="主题名称">
          <el-input v-model="form.topicName" placeholder="请输入主题名称" />
        </el-form-item>
        <el-form-item label="技能描述">
          <el-input v-model="form.description" type="textarea" :rows="4" placeholder="请输入技能描述" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary">生成技能</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive } from 'vue'

const form = reactive({
  topicName: '',
  description: ''
})
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
