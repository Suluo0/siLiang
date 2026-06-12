<template>
  <el-dialog v-model="visible" title="完善你的学习偏好" width="500px" :close-on-click-modal="false" class="prefs-dialog">
    <p class="prefs-hint">填写以下信息，我们将为你推荐更合适的面试题</p>

    <el-form :model="form" label-position="top">
      <el-form-item label="目标岗位">
        <el-select v-model="form.target_position" placeholder="请选择" clearable style="width:100%">
          <el-option v-for="p in positions" :key="p.id" :label="p.name" :value="p.name" />
        </el-select>
      </el-form-item>

      <el-form-item label="学习偏好 (可多选)">
        <el-select v-model="form.learning_preference" multiple placeholder="选择偏好方向" style="width:100%">
          <el-option v-for="t in tagOptions" :key="t" :label="t" :value="t" />
        </el-select>
      </el-form-item>

      <el-form-item label="经验水平">
        <el-radio-group v-model="form.experience_level">
          <el-radio value="初级">初级</el-radio>
          <el-radio value="中级">中级</el-radio>
          <el-radio value="高级">高级</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="每日学习目标 (题)">
        <el-input-number v-model="form.today_target" :min="0" :max="50" />
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="prefs-footer">
        <el-button text @click="skipForever">永不弹出</el-button>
        <el-button @click="skipLater">稍后再填</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/api/request'

const props = defineProps({ show: Boolean })
const emit = defineEmits(['done'])

const visible = ref(false)
const saving = ref(false)
const positions = ref([])
const tagOptions = ['Java', 'Python', '前端', '数据库', 'Spring', 'Redis', '分布式', '消息队列', '算法', '系统设计']

const form = ref({
  target_position: '',
  learning_preference: [],
  experience_level: '',
  today_target: 5
})

onMounted(async () => {
  try {
    const res = await request.get('/topic/positions')
    positions.value = res.items || []
  } catch {}
})

// sync prop with local visible
import { watch } from 'vue'
watch(() => props.show, (v) => { visible.value = v }, { immediate: true })
watch(visible, (v) => { if (!v) emit('done') })

function skipLater() {
  visible.value = false
}

function skipForever() {
  localStorage.setItem('skip_prefs_modal', 'true')
  visible.value = false
  ElMessage.success('可在右上角用户中心填写偏好')
}

async function save() {
  saving.value = true
  try {
    await request.post('/auth/preferences', {
      target_position: form.value.target_position,
      learning_preference: (form.value.learning_preference || []).join(','),
      experience_level: form.value.experience_level,
      today_target: form.value.today_target
    })
    ElMessage.success('偏好已保存')
    visible.value = false
  } catch (e) {
    ElMessage.error('保存失败')
  } finally { saving.value = false }
}
</script>

<style scoped>
.prefs-hint { color: #999; font-size: 14px; margin: 0 0 16px; }
.prefs-footer { display: flex; justify-content: flex-end; gap: 8px; }
</style>
