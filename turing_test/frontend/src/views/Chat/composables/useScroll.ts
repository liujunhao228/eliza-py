/**
 * 滚动控制 Composable
 *
 * 负责：
 * - 滚动到顶部/底部
 * - 滚动位置监控
 * - 滚动按钮显示控制
 */

import { ref, nextTick } from 'vue'

export function useScroll() {
  const messageListRef = ref<HTMLElement | null>(null)
  const showScrollButton = ref(false)

  /**
   * 滚动到底部
   */
  function scrollToBottom(): void {
    nextTick(() => {
      const container = messageListRef.value
      if (container) {
        container.scrollTo({
          top: container.scrollHeight,
          behavior: 'smooth'
        })
      }
    })
  }

  /**
   * 检查是否需要显示滚动按钮
   */
  function checkScroll(): void {
    const container = messageListRef.value
    if (container) {
      const { scrollTop, scrollHeight, clientHeight } = container
      showScrollButton.value = scrollHeight - scrollTop - clientHeight > 200
    }
  }

  /**
   * 处理滚动事件
   */
  function handleScroll(): void {
    checkScroll()
  }

  /**
   * 处理窗口大小变化
   */
  function handleResize(): void {
    checkScroll()
  }

  // 添加滚动事件监听
  function setupScrollListener() {
    const container = messageListRef.value
    if (container) {
      container.addEventListener('scroll', handleScroll)
    }
    window.addEventListener('resize', handleResize)
  }

  // 移除滚动事件监听
  function cleanupScrollListener() {
    const container = messageListRef.value
    if (container) {
      container.removeEventListener('scroll', handleScroll)
    }
    window.removeEventListener('resize', handleResize)
  }

  return {
    // 引用
    messageListRef,
    showScrollButton,
    // 方法
    scrollToBottom,
    checkScroll,
    setupScrollListener,
    cleanupScrollListener
  }
}
