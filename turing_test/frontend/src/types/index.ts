// 统一导出所有类型
// 基础 API 类型
export * from './api'
// 游戏相关类型
export * from './game'

// Result 组件专用展示类型
export type {
  SurveyData,
  ScoreBreakdownDisplay,
  GameResultResponse,
  OpponentTypeConfig,
  ConfidenceLevelConfig,
  SelfRoleConfig
} from './result'
