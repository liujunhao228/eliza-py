<template>
  <div class="game-info">
    <h2 class="session-title">
      <el-icon><ChatDotRound /></el-icon>
      聊天室
    </h2>
    <div class="turn-info">
      <span class="turn-label">第 {{ currentTurn }} 轮</span>
      <span v-if="metaCount > 0" class="meta-count">
        元对话 {{ metaCount }} 次
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ChatDotRound } from '@element-plus/icons-vue'

interface Props {
  turn: number
  metaCount: number
}

const props = defineProps<Props>()

// 计算当前轮数（双方各发一句算一轮）
const currentTurn = computed(() => Math.ceil(props.turn / 2))
</script>

<style scoped>
.game-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  min-width: 0;
}

.session-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.session-title .el-icon {
  color: var(--color-primary);
  font-size: 20px;
}

.turn-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.turn-label {
  font-size: 14px;
  color: var(--text-secondary);
  font-weight: 500;
  padding: 2px 8px;
  background: var(--bg-secondary);
  border-radius: var(--rounded-sm);
}

.meta-count {
  font-size: 13px;
  color: var(--color-amber-600);
  font-weight: 500;
}
</style>
