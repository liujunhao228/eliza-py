# 通用 UI 组件库使用指南

本文档介绍 `src/components/common` 目录下的通用 UI 组件的使用方法。

## 目录结构

```
src/components/common/
├── BaseButton.vue    # 基础按钮组件
├── BaseCard.vue      # 基础卡片组件
├── BaseInput.vue     # 基础输入框组件
├── BaseLoading.vue   # 基础加载组件
├── BaseEmpty.vue     # 基础空状态组件
├── BaseModal.vue     # 基础对话框组件
├── BaseToast.vue     # 基础提示组件
├── BaseProgress.vue  # 基础进度条组件
├── BaseBadge.vue     # 基础徽章组件
└── index.ts          # 统一导出文件
```

## 全局注册（可选）

在 `main.ts` 中全局注册所有通用组件：

```typescript
import { createApp } from 'vue'
import App from './App.vue'
import { installCommonComponents } from '@/components/common'

const app = createApp(App)

// 全局注册所有通用组件
app.use(installCommonComponents)

app.mount('#app')
```

## 按需导入

```vue
<script setup lang="ts">
import { BaseButton, BaseCard, BaseInput } from '@/components/common'
</script>
```

---

## 组件详情

### 1. BaseButton - 基础按钮

#### 使用示例

```vue
<template>
  <!-- 主要按钮 -->
  <BaseButton type="primary" @click="handleSubmit">
    提交
  </BaseButton>

  <!-- 带图标按钮 -->
  <BaseButton type="success" :icon="CheckIcon">
    确认
  </BaseButton>

  <!-- 加载状态 -->
  <BaseButton type="primary" loading>
    加载中...
  </BaseButton>

  <!-- 禁用状态 -->
  <BaseButton type="default" disabled>
    禁用
  </BaseButton>

  <!-- 块级按钮 -->
  <BaseButton type="primary" block>
    宽按钮
  </BaseButton>

  <!-- 纯图标按钮 -->
  <BaseButton type="info" icon-only :icon="SearchIcon" />
</template>

<script setup lang="ts">
import { BaseButton } from '@/components/common'
import { Check, Search } from '@element-plus/icons-vue'

const CheckIcon = Check
const SearchIcon = Search
</script>
```

#### Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| type | `'primary' \| 'success' \| 'warning' \| 'danger' \| 'info' \| 'default'` | `'default'` | 按钮类型 |
| size | `'small' \| 'medium' \| 'large'` | `'medium'` | 按钮尺寸 |
| disabled | `boolean` | `false` | 是否禁用 |
| loading | `boolean` | `false` | 是否加载中 |
| block | `boolean` | `false` | 是否为块级按钮 |
| icon | `Component` | `-` | 图标组件 |
| icon-only | `boolean` | `false` | 是否为纯图标按钮 |
| native-type | `'button' \| 'submit' \| 'reset'` | `'button'` | 原生 type 属性 |

#### Events

| 事件名 | 参数 | 说明 |
|--------|------|------|
| click | `(event: MouseEvent)` | 点击事件 |

---

### 2. BaseCard - 基础卡片

#### 使用示例

```vue
<template>
  <BaseCard title="卡片标题" shadow="hover">
    <p>卡片内容</p>
    
    <template #footer>
      <BaseButton type="primary" size="small">操作</BaseButton>
    </template>
  </BaseCard>
</template>

<script setup lang="ts">
import { BaseCard, BaseButton } from '@/components/common'
</script>
```

#### Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| title | `string` | `''` | 卡片标题 |
| shadow | `'always' \| 'hover' \| 'never'` | `'always'` | 阴影效果 |
| hoverable | `boolean` | `false` | 是否可悬浮 |
| bordered | `boolean` | `true` | 是否显示边框 |
| custom-style | `Record<string, string>` | `{}` | 自定义样式 |

#### Slots

| 插槽名 | 说明 |
|--------|------|
| default | 卡片主体内容 |
| header | 卡片头部（覆盖 title） |
| footer | 卡片底部 |

---

### 3. BaseInput - 基础输入框

#### 使用示例

```vue
<template>
  <!-- 基础输入框 -->
  <BaseInput v-model="username" label="用户名" placeholder="请输入用户名" />

  <!-- 密码输入框 -->
  <BaseInput v-model="password" type="password" label="密码" show-password />

  <!-- 带清除按钮 -->
  <BaseInput v-model="search" clearable placeholder="搜索..." />

  <!-- 带图标 -->
  <BaseInput v-model="email" prefix-icon="Mail" placeholder="邮箱" />

  <!-- 错误状态 -->
  <BaseInput v-model="invalid" error="请输入有效的邮箱地址" />

  <!-- 带辅助文字 -->
  <BaseInput v-model="phone" helper-text="请输入 11 位手机号" />
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { BaseInput } from '@/components/common'

const username = ref('')
const password = ref('')
const search = ref('')
const email = ref('')
const invalid = ref('')
const phone = ref('')
</script>
```

#### Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| model-value | `string \| number` | `''` | 绑定值 |
| type | `string` | `'text'` | 输入框类型 |
| size | `'small' \| 'medium' \| 'large'` | `'medium'` | 输入框尺寸 |
| label | `string` | `''` | 标签文本 |
| placeholder | `string` | `''` | 占位符 |
| disabled | `boolean` | `false` | 是否禁用 |
| readonly | `boolean` | `false` | 是否只读 |
| required | `boolean` | `false` | 是否必填 |
| error | `string` | `''` | 错误提示 |
| helper-text | `string` | `''` | 辅助文字 |
| prefix-icon | `Component` | `-` | 前缀图标 |
| suffix-icon | `Component` | `-` | 后缀图标 |
| clearable | `boolean` | `false` | 是否显示清除按钮 |
| show-password | `boolean` | `false` | 是否显示密码切换按钮 |
| maxlength | `number` | `-` | 最大长度 |
| minlength | `number` | `-` | 最小长度 |

#### Events

| 事件名 | 参数 | 说明 |
|--------|------|------|
| update:model-value | `(value: string)` | 值变化事件 |
| focus | `(event: FocusEvent)` | 聚焦事件 |
| blur | `(event: FocusEvent)` | 失焦事件 |
| clear | `-` | 清除事件 |
| keydown | `(event: KeyboardEvent)` | 键盘事件 |

#### Slots

| 插槽名 | 说明 |
|--------|------|
| prefix | 前缀内容 |
| suffix | 后缀内容 |

---

### 4. BaseLoading - 基础加载组件

#### 使用示例

```vue
<template>
  <!-- 全屏加载 -->
  <BaseLoading :loading="isLoading" fullscreen text="加载中..." />

  <!-- 内联加载 -->
  <BaseLoading inline :loading="true" size="small" />

  <!-- 自定义文本 -->
  <BaseLoading :loading="true" text="正在处理...">
    自定义加载文本
  </BaseLoading>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { BaseLoading } from '@/components/common'

const isLoading = ref(true)
</script>
```

#### Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| loading | `boolean` | `true` | 是否显示加载 |
| text | `string` | `'加载中...'` | 加载文本 |
| size | `'small' \| 'medium' \| 'large'` | `'medium'` | 加载器尺寸 |
| fullscreen | `boolean` | `false` | 是否全屏模式 |
| inline | `boolean` | `false` | 是否内联模式 |

#### Slots

| 插槽名 | 说明 |
|--------|------|
| default | 自定义加载文本 |

---

### 5. BaseEmpty - 基础空状态

#### 使用示例

```vue
<template>
  <BaseEmpty 
    title="暂无数据" 
    description="还没有任何内容，请稍后再试"
  >
    <template #action>
      <BaseButton type="primary" @click="handleRefresh">
        刷新
      </BaseButton>
    </template>
  </BaseEmpty>
</template>

<script setup lang="ts">
import { BaseEmpty, BaseButton } from '@/components/common'

const handleRefresh = () => {
  // 刷新逻辑
}
</script>
```

#### Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| title | `string` | `'暂无数据'` | 标题文本 |
| description | `string` | `''` | 描述文本 |
| size | `'small' \| 'medium' \| 'large'` | `'medium'` | 组件尺寸 |

#### Slots

| 插槽名 | 说明 |
|--------|------|
| icon | 自定义图标 |
| description | 自定义描述 |
| action | 操作按钮区域 |

---

### 6. BaseModal - 基础对话框

#### 使用示例

```vue
<template>
  <BaseButton type="primary" @click="showModal = true">
    打开对话框
  </BaseButton>

  <BaseModal
    v-model="showModal"
    title="确认操作"
    size="medium"
    :show-footer="true"
    @confirm="handleConfirm"
    @cancel="handleCancel"
  >
    <p>您确定要执行此操作吗？</p>
  </BaseModal>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { BaseModal, BaseButton } from '@/components/common'

const showModal = ref(false)

const handleConfirm = () => {
  // 确认逻辑
  showModal.value = false
}

const handleCancel = () => {
  // 取消逻辑
  showModal.value = false
}
</script>
```

#### Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| model-value | `boolean` | `false` | 是否显示对话框 |
| title | `string` | `''` | 对话框标题 |
| size | `'small' \| 'medium' \| 'large' \| 'fullscreen'` | `'medium'` | 对话框尺寸 |
| closable | `boolean` | `true` | 是否显示关闭按钮 |
| close-on-click-outside | `boolean` | `true` | 是否点击外部关闭 |
| center | `boolean` | `true` | 是否居中 |
| fullscreen | `boolean` | `false` | 是否全屏 |
| show-header | `boolean` | `true` | 是否显示头部 |
| show-footer | `boolean` | `false` | 是否显示底部 |
| show-cancel | `boolean` | `true` | 是否显示取消按钮 |
| show-confirm | `boolean` | `true` | 是否显示确认按钮 |
| cancel-text | `string` | `'取消'` | 取消按钮文本 |
| confirm-text | `string` | `'确定'` | 确认按钮文本 |
| confirm-loading | `boolean` | `false` | 确认按钮加载状态 |

#### Events

| 事件名 | 参数 | 说明 |
|--------|------|------|
| update:model-value | `(value: boolean)` | 显示状态变化 |
| close | `-` | 关闭事件 |
| cancel | `-` | 取消事件 |
| confirm | `-` | 确认事件 |

#### Slots

| 插槽名 | 说明 |
|--------|------|
| default | 对话框主体内容 |
| header | 自定义头部 |
| footer | 自定义底部 |
| footer-buttons | 自定义底部按钮 |

---

### 7. BaseToast - 基础提示组件

#### 使用示例

```vue
<template>
  <div>
    <BaseButton @click="showSuccess">成功提示</BaseButton>
    <BaseButton @click="showError">错误提示</BaseButton>
    <BaseButton @click="showWarning">警告提示</BaseButton>
    <BaseButton @click="showInfo">信息提示</BaseButton>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { BaseButton } from '@/components/common'
import { showToast } from '@/composables/useToast'

const showSuccess = () => {
  showToast.success('操作成功！')
}

const showError = () => {
  showToast.error('操作失败，请重试')
}

const showWarning = () => {
  showToast.warning('请注意此操作有风险')
}

const showInfo = () => {
  showToast.info('系统维护通知')
}
</script>
```

#### useToast 组合式 API

```typescript
// composables/useToast.ts
import { showToast } from '@/components/common'

export function useToast() {
  const showSuccess = (message: string) => {
    showToast({ type: 'success', message })
  }
  
  const showError = (message: string) => {
    showToast({ type: 'error', message })
  }
  
  const showWarning = (message: string) => {
    showToast({ type: 'warning', message })
  }
  
  const showInfo = (message: string) => {
    showToast({ type: 'info', message })
  }
  
  return { showSuccess, showError, showWarning, showInfo }
}
```

#### ToastOptions

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| type | `'success' \| 'error' \| 'warning' \| 'info'` | `'info'` | 提示类型 |
| title | `string` | `''` | 标题 |
| message | `string` | `''` | 消息内容 |
| duration | `number` | `3000` | 持续时间（毫秒） |
| position | `'top-left' \| 'top-center' \| 'top-right' \| 'bottom-left' \| 'bottom-center' \| 'bottom-right'` | `'top-right'` | 显示位置 |
| closable | `boolean` | `true` | 是否显示关闭按钮 |

---

### 8. BaseProgress - 基础进度条

#### 使用示例

```vue
<template>
  <!-- 基础进度条 -->
  <BaseProgress :percentage="50" />

  <!-- 带文本 -->
  <BaseProgress :percentage="75" show-text />

  <!-- 成功类型 -->
  <BaseProgress :percentage="100" type="success" show-text />

  <!-- 条纹动画 -->
  <BaseProgress :percentage="60" striped animated />

  <!-- 自定义文本 -->
  <BaseProgress :percentage="progress" show-text>
    <template #default="{ percentage }">
      {{ percentage }}% - 自定义文本
    </template>
  </BaseProgress>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { BaseProgress } from '@/components/common'

const progress = ref(60)
</script>
```

#### Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| percentage | `number` | `0` | 百分比（0-100） |
| type | `'primary' \| 'success' \| 'warning' \| 'danger' \| 'info'` | `'primary'` | 进度条类型 |
| size | `'small' \| 'medium' \| 'large'` | `'medium'` | 进度条尺寸 |
| show-text | `boolean` | `false` | 是否显示文本 |
| striped | `boolean` | `false` | 是否条纹效果 |
| animated | `boolean` | `false` | 是否动画效果 |

#### Slots

| 插槽名 | 参数 | 说明 |
|--------|------|------|
| default | `{ percentage: number }` | 自定义文本内容 |

---

### 9. BaseBadge - 基础徽章

#### 使用示例

```vue
<template>
  <!-- 基础徽章 -->
  <BaseBadge :value="5" />

  <!-- 带类型 -->
  <BaseBadge :value="10" type="success" />

  <!-- 超过最大值 -->
  <BaseBadge :value="100" :max="99" />

  <!-- 圆点模式 -->
  <BaseBadge is-dot type="danger" />

  <!-- 隐藏徽章 -->
  <BaseBadge :value="5" :hidden="true" />

  <!-- 绝对定位 -->
  <BaseBadge :value="5" absolute class="badge-top-right">
    <BaseButton>消息</BaseButton>
  </BaseBadge>
</template>

<script setup lang="ts">
import { BaseBadge, BaseButton } from '@/components/common'
</script>

<style scoped>
.badge-top-right {
  --badge-offset-top: 8px;
  --badge-offset-right: 8px;
}
</style>
```

#### Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| value | `string \| number` | `''` | 显示值 |
| max | `number` | `99` | 最大值（超过显示 N+） |
| type | `'primary' \| 'success' \| 'warning' \| 'danger' \| 'info'` | `'danger'` | 徽章类型 |
| size | `'small' \| 'medium' \| 'large'` | `'medium'` | 徽章尺寸 |
| is-dot | `boolean` | `false` | 是否为圆点模式 |
| absolute | `boolean` | `false` | 是否绝对定位 |
| hidden | `boolean` | `false` | 是否隐藏 |
| offset | `[number, number]` | `[0, 0]` | 偏移量 [top, right] |

---

## 主题定制

所有通用组件都使用项目的主题系统，支持亮色/暗色主题自动切换。

主题变量定义在 `src/styles/theme.css` 中，可以通过覆盖 CSS 变量来自定义组件样式：

```css
:root {
  --color-primary: #your-color;
  --rounded-md: 8px;
  /* ... */
}
```

---

## 响应式设计

所有组件都支持响应式设计，适配从手机到 4K 屏幕的各种设备尺寸。
