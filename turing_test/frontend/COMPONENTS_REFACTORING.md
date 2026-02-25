# 通用组件库重构总结

## 概述

本次重构提取了前端项目中的通用 UI 组件，创建了可复用的组件库，并更新了现有代码以使用这些新组件。

## 完成的工作

### 1. 创建的通用组件

在 `src/components/common/` 目录下创建了以下 9 个基础组件：

| 组件名 | 文件 | 功能描述 |
|--------|------|----------|
| BaseButton | `BaseButton.vue` | 基础按钮组件，支持多种类型、尺寸、加载状态 |
| BaseCard | `BaseCard.vue` | 基础卡片组件，支持头部、主体、底部插槽 |
| BaseInput | `BaseInput.vue` | 基础输入框组件，支持多种类型、验证、图标 |
| BaseLoading | `BaseLoading.vue` | 基础加载组件，支持全屏和内联模式 |
| BaseEmpty | `BaseEmpty.vue` | 基础空状态组件，支持自定义图标和操作 |
| BaseModal | `BaseModal.vue` | 基础对话框组件，支持多种尺寸和配置 |
| BaseToast | `BaseToast.vue` | 基础提示组件，支持多种类型和位置 |
| BaseProgress | `BaseProgress.vue` | 基础进度条组件，支持条纹动画效果 |
| BaseBadge | `BaseBadge.vue` | 基础徽章组件，支持数字和圆点模式 |

### 2. 配套工具

- **统一导出文件**：`src/components/common/index.ts`
  - 提供组件的按需导入
  - 提供全局注册函数 `installCommonComponents`

- **组合式 API**：`src/composables/useToast.ts`
  - `useToast()` - 在组件中便捷使用 Toast
  - `showSuccess()` / `showError()` / `showWarning()` / `showInfo()` - 快捷方法

- **使用文档**：`docs/common-components.md`
  - 详细的组件使用示例
  - Props 和 Events 说明
  - Slot 说明

### 3. 更新的现有代码

| 文件 | 更新内容 |
|------|----------|
| `views/Login.vue` | 使用 BaseCard、BaseInput、BaseButton 替换 Element Plus 组件 |
| `views/Profile.vue` | 使用 BaseButton、BaseLoading、BaseEmpty、BaseModal 重构状态和对话框 |
| `components/Chat/ChatInput.vue` | 使用 BaseButton 替换 el-button |
| `components/Lobby/MatchingSection.vue` | 使用 BaseCard、BaseProgress、BaseButton 重构 |

## 组件特性

### 1. 主题系统
所有组件都使用项目的 CSS 变量主题系统：
- 支持亮色/暗色主题自动切换
- 使用 `var(--color-primary)` 等变量
- 遵循统一的设计规范

### 2. 响应式设计
所有组件都支持响应式：
- 适配从 360px 到 4K 屏幕
- 使用 CSS 媒体查询
- 移动端优化

### 3. 无障碍支持
- 适当的 ARIA 属性
- 键盘导航支持
- 焦点状态指示

### 4. 动画效果
- 平滑的过渡动画
- 加载动画
- 悬浮效果

## 使用方法

### 方式一：按需导入（推荐）

```vue
<script setup lang="ts">
import { BaseButton, BaseCard, BaseInput } from '@/components/common'
</script>

<template>
  <BaseCard>
    <BaseInput v-model="text" label="输入" />
    <BaseButton type="primary" @click="submit">提交</BaseButton>
  </BaseCard>
</template>
```

### 方式二：全局注册

在 `main.ts` 中：

```typescript
import { createApp } from 'vue'
import App from './App.vue'
import { installCommonComponents } from '@/components/common'

const app = createApp(App)

// 全局注册所有通用组件
app.use(installCommonComponents)

app.mount('#app')
```

然后在组件中直接使用：

```vue
<template>
  <BaseButton type="primary">按钮</BaseButton>
</template>
```

### 方式三：使用 Toast API

```vue
<script setup lang="ts">
import { useToast } from '@/composables/useToast'

const { success, error, warning, info } = useToast()

const handleSubmit = () => {
  try {
    // 业务逻辑
    success('操作成功！')
  } catch (e) {
    error('操作失败，请重试')
  }
}
</script>
```

## 迁移指南

### 从 Element Plus 迁移

| Element Plus | 通用组件 | 备注 |
|--------------|----------|------|
| `<el-button>` | `<BaseButton>` | API 基本一致 |
| `<el-input>` | `<BaseInput>` | 支持 v-model |
| `<el-card>` | `<BaseCard>` | 插槽名称相同 |
| `<el-dialog>` | `<BaseModal>` | 使用 v-model 控制显示 |
| `<el-progress>` | `<BaseProgress>` | API 简化 |
| `<el-badge>` | `<BaseBadge>` | 功能类似 |

### 注意事项

1. **样式覆盖**：如需自定义样式，使用 CSS 变量或添加自定义 class
2. **图标**：组件支持传入图标组件，使用 `#icon` 插槽或 `icon` prop
3. **事件**：保持与 Element Plus 类似的事件命名

## 后续优化建议

1. **添加更多组件**
   - BaseSelect - 下拉选择框
   - BaseTable - 数据表格
   - BaseTabs - 标签页
   - BaseDropdown - 下拉菜单

2. **单元测试**
   - 为每个组件添加 Vitest 测试
   - 测试覆盖率目标 80%+

3. **文档站点**
   - 使用 VitePress 创建组件文档站点
   - 提供在线示例和 Playground

4. **主题定制工具**
   - 创建主题配置生成器
   - 支持在线预览和导出

5. **性能优化**
   - 按需加载组件
   - 添加组件懒加载支持

## 文件结构

```
src/
├── components/
│   ├── common/              # 通用组件库
│   │   ├── BaseButton.vue
│   │   ├── BaseCard.vue
│   │   ├── BaseInput.vue
│   │   ├── BaseLoading.vue
│   │   ├── BaseEmpty.vue
│   │   ├── BaseModal.vue
│   │   ├── BaseToast.vue
│   │   ├── BaseProgress.vue
│   │   ├── BaseBadge.vue
│   │   └── index.ts
│   ├── Chat/                # 聊天相关组件
│   ├── Lobby/               # 大厅相关组件
│   └── ...
├── composables/
│   └── useToast.ts          # Toast 组合式 API
└── styles/
    └── theme.css            # 主题样式
```

## 总结

通过提取通用组件：
- ✅ 提高了代码复用性
- ✅ 统一了 UI 风格
- ✅ 减少了重复代码
- ✅ 便于维护和扩展
- ✅ 支持主题切换
- ✅ 完整的响应式设计
