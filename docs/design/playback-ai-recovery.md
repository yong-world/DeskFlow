# 回放引擎与 AI 异常恢复设计

## 1. 回放引擎概述

回放引擎的核心设计原则：**正常走流程，出问题回退，AI 跨过障碍**。

```
正常执行路径（快速、确定性强）
  │
  │ 遇到异常
  ▼
常规重试（同样的方式再试几次）
  │
  │ 仍然失败
  ▼
回退到稳定点 + AI 接管（慢但智能）
  │
  │ AI 也解决不了
  ▼
暂停 + 人工介入通知
```

## 2. 回放状态机

### 2.1 状态定义

```
┌───────────┐
│  IDLE     │  流程未开始
└─────┬─────┘
      │ start()
      ▼
┌───────────┐     pause()     ┌───────────┐
│ RUNNING   │────────────────►│  PAUSED   │
│           │◄────────────────│           │
└─────┬─────┘     resume()    └───────────┘
      │
      ├──── 步骤成功 ────► 继续下一步 ──► (回到 RUNNING)
      │
      ├──── 步骤失败 ────►┌───────────┐
      │                  │ RETRYING  │  常规重试（最多 N 次）
      │                  └─────┬─────┘
      │                        │
      │               重试成功 ─┤─ 重试失败
      │               回RUNNING │
      │                        ▼
      │                  ┌───────────┐
      │                  │RECOVERING │  AI 异常恢复
      │                  └─────┬─────┘
      │                        │
      │              恢复成功 ──┤── 恢复失败
      │              回RUNNING  │
      │                        ▼
      │                  ┌───────────┐
      │                  │ BLOCKED   │  等待人工介入
      │                  └─────┬─────┘
      │                        │ manual_resolve()
      │                        │ 回 RUNNING
      │
      ├──── 所有步骤完成 ─►┌───────────┐
      │                   │ COMPLETED │
      │                   └───────────┘
      │
      └──── 致命错误 ────►┌───────────┐
                         │  FAILED   │
                         └───────────┘
```

### 2.2 状态转换事件

| 当前状态 | 事件 | 目标状态 | 动作 |
|---------|------|---------|------|
| IDLE | start | RUNNING | 加载流程，初始化变量，执行第一步 |
| RUNNING | step_success | RUNNING | 保存结果，执行下一步 |
| RUNNING | step_fail | RETRYING | 记录错误，开始重试 |
| RUNNING | all_done | COMPLETED | 输出报告，清理资源 |
| RUNNING | pause | PAUSED | 保存当前状态 |
| RUNNING | fatal_error | FAILED | 截图，保存现场，通知 |
| RETRYING | retry_success | RUNNING | 继续下一步 |
| RETRYING | retry_exhausted | RECOVERING | 触发 AI 恢复 |
| RECOVERING | recovery_success | RUNNING | 应用 AI 的恢复步骤，继续 |
| RECOVERING | recovery_fail | BLOCKED | 暂停等待人工 |
| BLOCKED | manual_resolve | RUNNING | 用户手动处理后继续 |
| PAUSED | resume | RUNNING | 恢复执行 |

## 3. 步骤执行器 (StepExecutor)

### 3.1 单步执行流程

```
执行一个 Step:
│
├─ 1. 前置检查
│    ├── 检查 wait_until 前置条件
│    ├── 检查变量是否就绪
│    └── 检查目标窗口/页面是否存在
│
├─ 2. 元素定位（按优先级）
│    ├── 尝试 primary locator
│    │    └── 成功? → 使用此元素
│    ├── 尝试 secondary locator
│    │    └── 成功? → 使用此元素
│    ├── 尝试 tertiary locator
│    │    └── 成功? → 使用此元素
│    ├── 尝试 fallback (图像匹配)
│    │    └── 成功? → 使用此坐标
│    └── 全部失败 → 抛出 ElementNotFound
│
├─ 3. 执行操作
│    ├── 点击 / 输入 / 快捷键 / ...
│    └── 记录操作耗时
│
├─ 4. 后置验证
│    ├── 检查 wait_until 后置条件
│    ├── 验证控件值是否变化
│    ├── 截图保存（用于对比和调试）
│    └── 记录步骤结果
│
└─ 5. 输出
     ├── 成功 → StepResult(success=True, ...)
     └── 失败 → StepResult(success=False, error=...)
```

### 3.2 执行结果记录

```json
{
  "step_id": "step_12",
  "step_name": "点击查询",
  "status": "success",
  "started_at": "2026-03-31T10:24:15.123",
  "completed_at": "2026-03-31T10:24:16.456",
  "duration_ms": 1333,
  "locator_used": "primary (css_selector: button.search-btn)",
  "retry_count": 0,
  "screenshot_path": "runs/run_001/step_12.png",
  "variables_changed": {
    "__last_click_target__": "button.search-btn"
  },
  "notes": null
}
```

## 4. 常规重试机制

### 4.1 重试策略

```yaml
retry:
  max_attempts: 3
  interval_ms: 2000          # 重试间隔
  backoff: exponential       # 退避策略: fixed / linear / exponential
  max_interval_ms: 10000     # 最大间隔

  # 每次重试前的操作
  before_retry:
    - screenshot                  # 截图记录当前状态
    - refresh_ui_tree             # 刷新控件树缓存

  # 可重试的错误类型
  retryable_errors:
    - ElementNotFound             # 控件没找到
    - ElementNotEnabled           # 控件不可用
    - ElementNotVisible           # 控件不可见
    - WindowNotFound              # 窗口没找到
    - TimeoutError                # 等待超时
    - ClickIntercepted            # 点击被遮挡

  # 不可重试的错误
  non_retryable_errors:
    - ProcessCrashed              # 目标进程崩溃
    - NetworkError                # 网络不通
    - ScriptError                 # 自定义脚本报错
    - PermissionDenied            # 权限不足
```

### 4.2 重试间隔计算

```
fixed:        interval_ms (固定)
linear:       interval_ms * attempt_number
exponential:  interval_ms * 2^(attempt_number - 1)

示例 (exponential, interval=2000):
  第1次重试: 2000ms 后
  第2次重试: 4000ms 后
  第3次重试: 8000ms 后 (不超过 max_interval_ms)
```

## 5. Checkpoint（稳定点）机制

### 5.1 稳定点定义

稳定点 = 可以安全重新开始执行的位置。回退到稳定点后，后续步骤可以正确重新执行。

### 5.2 自动识别规则

| 场景 | 识别条件 | 原因 |
|------|---------|------|
| 应用启动 | action=launch_app 且 wait_until 通过 | 应用打开是干净状态 |
| 窗口打开 | action=switch_window 或新窗口出现 | 窗口切换是天然分界 |
| 页面导航 | action=web_navigate | URL 是确定性状态 |
| 登录完成 | 检测到登录后的首个操作 | 登录态是稳定前提 |
| 保存操作 | hotkey=ctrl+s 或 click 保存按钮 | 保存后数据持久化 |
| 表单重置 | 检测到清空/重置操作 | 空表单是干净状态 |

### 5.3 不适合做稳定点的位置

| 场景 | 原因 |
|------|------|
| 表单填写中途 | 回退会丢失已填内容，重新填写可能冲突 |
| 数据提交后确认页面未出现 | 可能导致重复提交 |
| 文件操作中途 | 文件可能处于不一致状态 |
| 弹窗/对话框打开时 | 回退不一定能复现弹窗 |
| 循环中间 | 回退可能导致循环次数错误 |

### 5.4 稳定点数据快照

每个稳定点保存一份状态快照：

```json
{
  "checkpoint_id": "cp_step_05",
  "step_id": "step_05",
  "timestamp": "2026-03-31T10:24:10.000",
  "snapshot": {
    "variables": {
      "month": "2026-03",
      "output_path": "D:/报表/",
      "file_saved": true
    },
    "window_state": {
      "active_window": "2026-03_销售报表.xlsx - Excel",
      "open_windows": ["Excel", "Chrome"]
    },
    "screenshot": "runs/run_001/checkpoint_step_05.png",
    "browser_state": {
      "url": null,
      "cookies_snapshot": null
    }
  },
  "rollback_actions": [
    "确保 Excel 窗口在前台",
    "确认文件已保存"
  ]
}
```

## 6. AI 异常恢复机制

### 6.1 触发条件

```
AI 恢复触发条件：
  1. 常规重试全部失败（已尝试 max_attempts 次）
  2. 步骤配置了 on_fail.strategy = "ai_retry"
  3. ai_recovery_enabled = true（全局开关）
```

### 6.2 恢复流程

```
┌───────────────────────────────────────────────┐
│ 步骤 1: 收集现场信息                             │
│                                               │
│  ├── 当前屏幕截图 (全屏)                        │
│  ├── 当前控件树 (精简版，只保留可见控件)           │
│  ├── 错误信息 (定位失败 / 超时 / 值不匹配)       │
│  ├── 目标步骤的定义 (action / locator / 语义)    │
│  ├── 最近 5 步的执行历史                        │
│  ├── 上一个稳定点的截图（正常状态参照）            │
│  └── 该步骤历次成功执行的截图 (如有)              │
└───────────────────┬───────────────────────────┘
                    ▼
┌───────────────────────────────────────────────┐
│ 步骤 2: AI 分析                                │
│                                               │
│  发送多模态请求给 LLM:                          │
│  ├── 系统提示: RPA 异常恢复专家角色              │
│  ├── 当前截图 + 历史截图                        │
│  ├── 错误上下文                                │
│  └── 请求: 分析原因 + 恢复方案                   │
│                                               │
│  AI 返回:                                      │
│  ├── 故障分析 (为什么失败)                       │
│  ├── 恢复步骤 (具体操作序列)                     │
│  ├── 置信度                                    │
│  └── 是否需要回退到稳定点                        │
└───────────────────┬───────────────────────────┘
                    ▼
┌───────────────────────────────────────────────┐
│ 步骤 3: 执行恢复                                │
│                                               │
│  方案A: 就地恢复（不需要回退）                    │
│    → 直接执行 AI 给出的替代操作序列              │
│    → 例如: 按钮位置变了，AI 找到新位置            │
│                                               │
│  方案B: 回退恢复（需要回退到稳定点）              │
│    → 回退到最近的 checkpoint                     │
│    → 恢复 checkpoint 的状态                     │
│    → 执行 AI 给出的修正路径                      │
│    → 例如: 弹了意料之外的对话框，需要关掉重来      │
│                                               │
│  方案C: 跳过（AI 认为此步骤可以跳过）              │
│    → 标记为 skipped                             │
│    → 继续后续步骤                                │
│    → 例如: 确认对话框没出现因为设置了不再提示       │
└───────────────────┬───────────────────────────┘
                    ▼
┌───────────────────────────────────────────────┐
│ 步骤 4: 验证恢复结果                             │
│                                               │
│  ├── 恢复后截图，与预期状态对比                   │
│  ├── 检查后续步骤的前置条件是否满足               │
│  └── 恢复成功 → 继续执行                         │
│      恢复失败 → 进入 BLOCKED 状态               │
└───────────────────────────────────────────────┘
```

### 6.3 AI 请求 Prompt 模板

```
## 系统角色

你是一个 RPA 桌面自动化异常恢复专家。用户的自动化流程在执行中遇到了问题，
你需要分析原因并给出具体的恢复操作。

## 当前任务

流程名称: {{workflow_name}}
当前步骤: {{step_name}} ({{step_id}})
步骤目标: {{step_description}}
操作类型: {{action_type}}

## 错误信息

错误类型: {{error_type}}
错误详情: {{error_message}}
已重试次数: {{retry_count}}

## 当前屏幕截图
[当前截图 - 图片]

## 历史截图（该步骤上次成功时）
[历史截图 - 图片]（如有）

## 上一个稳定点截图
[稳定点截图 - 图片]

## 当前控件树（精简）
{{ui_tree_summary}}

## 最近执行历史
{{recent_steps_history}}

## 请分析并回答

1. **故障原因**: 为什么这一步失败了？对比当前截图和历史截图，界面发生了什么变化？
2. **恢复方案**: 给出具体的恢复操作步骤（JSON 格式，使用标准 action 类型）
3. **是否需要回退**: 是否需要回退到上一个稳定点？为什么？
4. **置信度**: 你对恢复方案的置信度 (0-1)
5. **建议**: 是否需要永久更新流程定义？

请以以下 JSON 格式回答:
```

### 6.4 AI 恢复响应格式

```json
{
  "analysis": {
    "root_cause": "ERP系统更新后，导出按钮从工具栏移到了右上角的'更多操作'菜单中",
    "ui_changes_detected": [
      "工具栏按钮减少了",
      "右上角新增了'更多操作'按钮",
      "导出功能现在在下拉菜单里"
    ]
  },

  "recovery": {
    "type": "in_place",
    "needs_rollback": false,
    "steps": [
      {
        "action": "click",
        "description": "点击'更多操作'按钮",
        "locator": {
          "strategy": "ocr_text",
          "text": "更多操作",
          "region_pct": { "x": 0.8, "y": 0.0, "w": 0.2, "h": 0.1 }
        },
        "wait_until": {
          "type": "element_visible",
          "description": "等待下拉菜单出现"
        }
      },
      {
        "action": "click",
        "description": "在下拉菜单中点击'导出'",
        "locator": {
          "strategy": "ocr_text",
          "text": "导出"
        }
      }
    ]
  },

  "confidence": 0.82,

  "should_update_workflow": true,
  "update_suggestion": "将 step_13 的 locator 更新为先点击'更多操作'再点击'导出'的两步操作"
}
```

### 6.5 回退执行逻辑

```
回退到稳定点的具体操作：

1. 确定回退目标
   └── 找到当前步骤之前最近的 checkpoint

2. 恢复窗口状态
   ├── 关闭 checkpoint 之后打开的窗口/对话框
   ├── 切换到 checkpoint 记录的活动窗口
   └── 如果是 Web，导航到 checkpoint 记录的 URL

3. 恢复变量状态
   └── 将变量回滚到 checkpoint 保存的值

4. 验证环境状态
   ├── 截图对比（当前 vs checkpoint 截图）
   ├── 检查关键控件是否存在
   └── 确认可以从此处继续

5. 从稳定点重新执行
   ├── 如果 AI 提供了修正步骤 → 执行修正步骤
   └── 如果只是临时异常 → 重新执行原始步骤
```

## 7. 执行日志与报告

### 7.1 执行日志结构

```
runs/
└── run_20260331_102400/
    ├── run_metadata.json        # 执行元信息
    ├── execution_log.jsonl      # 逐步执行日志
    ├── screenshots/             # 每步截图
    │   ├── step_01.png
    │   ├── step_02.png
    │   └── ...
    ├── checkpoints/             # 稳定点快照
    │   ├── cp_step_05.json
    │   └── cp_step_10.json
    ├── ai_recovery/             # AI 恢复记录
    │   └── recovery_step_13.json
    └── report.html              # 可读的执行报告
```

### 7.2 执行报告内容

```
执行报告 - 月度销售报表导出
══════════════════════════════════

状态: ✅ 成功 (有 1 次 AI 恢复)
开始: 2026-03-31 10:24:00
结束: 2026-03-31 10:27:42
耗时: 3分42秒

步骤统计:
  总步骤: 35
  直接成功: 33
  重试后成功: 1 (step_08, 重试2次)
  AI恢复成功: 1 (step_13, 导出按钮位置变更)
  失败: 0
  跳过: 0

AI 恢复详情:
  step_13 "点击导出":
    原因: ERP更新后导出按钮移至下拉菜单
    恢复: 先点击"更多操作"再点击"导出"
    建议: 已自动更新流程定义

变量输出:
  output_file: D:/报表/2026-03_销售报表.xlsx
```

## 8. 流程自学习

### 8.1 自动优化机制

```
每次执行后的自动优化:

1. 定位器评分更新
   ├── 某个 locator 连续 5 次成功 → 提升优先级
   ├── 某个 locator 连续 3 次失败 → 降低优先级
   └── fallback locator 被使用 → 提示更新 primary

2. 等待时间优化
   ├── 统计每步实际等待时间
   ├── 如果平均等待远大于配置 → 建议增加 timeout
   └── 如果每次都秒过 → 建议减少 timeout

3. AI 恢复结果学习
   ├── AI 恢复成功且 should_update_workflow=true
   │   → 自动更新流程定义（需用户确认）
   ├── 同一步骤多次触发 AI 恢复
   │   → 标记为不稳定步骤，建议重新录制
   └── AI 恢复方案保存为知识库
       → 相似场景优先查本地知识库，不调 AI
```

### 8.2 知识库结构

```json
{
  "knowledge_id": "kb_001",
  "pattern": {
    "error_type": "ElementNotFound",
    "app": "用友U8",
    "context": "菜单项点击"
  },
  "solution": {
    "strategy": "ocr_text_fallback",
    "description": "用友U8菜单控件无法通过UIAutomation获取，使用OCR定位菜单文字"
  },
  "success_count": 12,
  "last_used": "2026-03-31"
}
```
