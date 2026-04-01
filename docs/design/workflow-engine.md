# 流程引擎设计

## 1. 概述

流程引擎是录制数据和回放执行之间的桥梁，负责：
1. **操作识别** — 将原始录制数据转化为结构化的操作步骤
2. **流程固化** — 将操作步骤固化为可编辑、可复用的流程包
3. **流程执行** — 加载流程包并按定义执行每一步

## 2. 操作识别管线

### 2.1 处理流水线

```
原始录制 events.jsonl
        │
        ▼
┌─────────────────────────────────────────────────┐
│ 阶段1: 预处理 (Preprocessing)                     │
│  - 噪音过滤（误点击、犹豫操作、无关窗口）              │
│  - 操作合并（连续输入、连续滚动、双击识别）            │
│  - 时间线规范化（去除等待时间，分析等待原因）           │
│  输入: 87 条原始事件 → 输出: 42 条有效事件            │
└─────────────────┬───────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────┐
│ 阶段2: 语义识别 (Semantic Recognition)             │
│  - 操作类型分类（点击/输入/快捷键/拖拽/选择）          │
│  - 操作目标识别（哪个控件、哪个菜单项、哪个按钮）       │
│  - 操作意图推断（"保存文件"、"切换Sheet"、"导出数据"）  │
│  - 置信度评分（每步操作的识别可信程度 0-1）            │
│  输出: 42 条带语义标注的操作                         │
└─────────────────┬───────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────┐
│ 阶段3: 定位器生成 (Locator Generation)             │
│  - 为每步生成最佳定位表达式                          │
│  - 评估定位器的稳定性（是否会因布局变化而失效）          │
│  - 生成多级 fallback 定位器                         │
│  输出: 42 条带定位器的操作                           │
└─────────────────┬───────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────┐
│ 阶段4: 等待条件推断 (Wait Condition Inference)      │
│  - 分析操作间的时间间隔                              │
│  - 推断等待原因（页面加载/控件出现/动画完成/数据就绪）   │
│  - 生成 wait_until 条件（取代固定 sleep）             │
│  输出: 42 条带等待条件的操作                          │
└─────────────────┬───────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────┐
│ 阶段5: 变量提取 (Variable Extraction)              │
│  - 识别重复出现的值（文件路径、日期、用户名、单号）      │
│  - 识别从界面读取后用于后续步骤的值                    │
│  - 将硬编码值替换为变量引用 {{variable_name}}         │
│  输出: 参数化的操作序列                              │
└─────────────────┬───────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────┐
│ 阶段6: AI 补全 (AI Completion)                     │
│  - 对置信度 < 0.7 的步骤，发送截图+上下文给 LLM        │
│  - AI 分析操作意图和最佳定位策略                       │
│  - AI 建议等待条件和错误处理方式                       │
│  - 人工确认 AI 的建议                                │
│  输出: 完整的操作序列（所有步骤置信度 > 0.7）           │
└─────────────────┬───────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────┐
│ 阶段7: 稳定点标记 (Checkpoint Marking)             │
│  - 自动识别适合做稳定点的位置                         │
│  - 标记：窗口打开、页面导航、登录完成、表单重置等        │
│  - 允许用户手动添加/移除稳定点                        │
│  输出: 带稳定点标记的完整流程                         │
└─────────────────────────────────────────────────┘
        │
        ▼
  固化为流程包 workflow.yaml
```

### 2.2 置信度评分规则

| 条件 | 置信度加分 | 说明 |
|------|----------|------|
| 有 AutomationId | +0.3 | 最可靠的定位标识 |
| 有 Name 且唯一 | +0.2 | 较可靠 |
| 控件类型明确 (Button/TextBox) | +0.15 | 标准控件 |
| 控件值变化可验证 | +0.15 | 操作效果可确认 |
| 有 OCR 可识别文字 | +0.1 | 文字定位兜底 |
| 截图模板清晰 | +0.1 | 图像匹配可用 |

| 条件 | 置信度减分 | 说明 |
|------|----------|------|
| 控件树获取失败 | -0.4 | 只能依赖坐标/图像 |
| 窗口标题动态变化 | -0.15 | 窗口定位不稳定 |
| 操作目标是 Canvas | -0.3 | 无控件信息 |
| 坐标在窗口边缘 | -0.1 | 可能是滚动条误触 |
| 操作间隔异常 | -0.1 | 可能有隐藏的加载过程 |

### 2.3 AI 补全的输入输出

**发送给 AI 的 Prompt 结构：**

```
你是一个 RPA 操作分析助手。用户录制了一个桌面自动化流程，
以下步骤的自动识别置信度较低，需要你分析。

## 当前步骤信息
- 操作类型: 鼠标左键单击
- 屏幕坐标: (1245, 387)
- 窗口: "用友U8 - 总账管理"
- 控件信息: 未获取到 (control.found = false)
- 操作前截图: [图片]
- 操作后截图: [图片]

## 上下文
- 前一步: 点击了"凭证" 菜单
- 后一步: 在输入框中输入了日期 "2026-03-01"

## 请分析
1. 这一步在做什么？（操作语义）
2. 推荐用什么方式定位这个操作目标？
3. 应该设置什么等待条件？
4. 操作失败时应该怎么恢复？
```

**AI 返回格式：**

```json
{
  "semantic": "点击'填制凭证'子菜单项",
  "recommended_locator": {
    "primary": { "strategy": "ocr_text", "text": "填制凭证" },
    "fallback": { "strategy": "image_match", "description": "菜单项图标+文字" }
  },
  "wait_condition": {
    "type": "window_appear",
    "window_title_contains": "填制凭证"
  },
  "on_fail": {
    "strategy": "retry_after_reopen_menu",
    "description": "重新打开凭证菜单，再点击填制凭证"
  },
  "confidence": 0.78,
  "notes": "用友U8的菜单控件通常无法通过UI Automation获取，建议使用OCR定位"
}
```

## 3. 流程包格式定义

### 3.1 流程包目录结构

```
workflows/
└── monthly_report_export/           # 流程包目录
    ├── workflow.yaml                # 流程定义（主文件）
    ├── manifest.json                # 包元信息
    ├── snapshots/                   # 操作截图（用于图像匹配）
    │   ├── step_03_export_btn.png
    │   ├── step_07_confirm_dialog.png
    │   └── ...
    ├── templates/                   # 模板文件（如报表模板）
    │   └── report_template.xlsx
    └── scripts/                     # 自定义脚本（高级用户）
        └── data_transform.py
```

### 3.2 包元信息 (manifest.json)

```json
{
  "id": "monthly_report_export",
  "name": "月度销售报表导出",
  "version": "1.2.0",
  "description": "从ERP系统导出月度销售数据，整理后填入Excel报表模板",
  "author": "张三",
  "created_at": "2026-03-15T14:30:00",
  "updated_at": "2026-03-31T10:00:00",

  "requirements": {
    "os": "Windows 10+",
    "apps": [
      { "name": "Microsoft Excel", "process": "EXCEL.EXE", "required": true },
      { "name": "Chrome", "process": "chrome.exe", "required": true }
    ],
    "screen_resolution_min": "1920x1080",
    "python_packages": ["playwright", "openpyxl"]
  },

  "variables": {
    "month": { "type": "string", "default": "2026-03", "description": "报表月份" },
    "output_path": { "type": "path", "default": "D:/报表/", "description": "输出目录" },
    "erp_url": { "type": "url", "default": "https://erp.company.com", "description": "ERP地址" }
  },

  "statistics": {
    "total_steps": 35,
    "estimated_duration_seconds": 180,
    "success_rate": 0.94,
    "total_runs": 47,
    "ai_assisted_steps": 3
  }
}
```

### 3.3 流程定义 (workflow.yaml)

```yaml
name: 月度销售报表导出
version: "1.2.0"
description: 从ERP系统导出月度销售数据，整理后填入Excel报表模板

# ============ 全局配置 ============
config:
  timeout_per_step: 30000          # 单步超时 ms
  retry_count: 3                   # 默认重试次数
  screenshot_on_error: true        # 出错时自动截图
  ai_recovery_enabled: true        # 启用 AI 异常恢复
  log_level: info

# ============ 变量定义 ============
variables:
  month:
    type: string
    default: "2026-03"
    prompt: "请输入报表月份 (YYYY-MM)"
  output_path:
    type: path
    default: "D:/报表/"
  erp_url:
    type: url
    default: "https://erp.company.com"

# ============ 流程步骤 ============
steps:

  # ---- 阶段1: 打开并准备 Excel ----
  - id: step_01
    name: 打开Excel模板
    action: launch_app
    params:
      path: "templates/report_template.xlsx"
      process: "EXCEL.EXE"
    wait_until:
      type: window_title_contains
      value: "report_template"
      timeout: 10000
    checkpoint: true               # 标记为稳定点
    confidence: 0.95

  - id: step_02
    name: 另存为本月报表
    action: hotkey
    params:
      keys: "F12"
    wait_until:
      type: window_title_contains
      value: "另存为"
      timeout: 5000
    confidence: 0.95

  - id: step_03
    name: 输入文件名
    action: type_text
    params:
      text: "{{month}}_销售报表.xlsx"
    locator:
      primary:
        strategy: uia
        automation_id: "FileNameControlHost"
        control_type: ComboBox
    confidence: 0.90

  - id: step_04
    name: 选择保存路径
    action: type_text
    params:
      text: "{{output_path}}"
    locator:
      primary:
        strategy: uia
        automation_id: "AddressBar"
    confidence: 0.85

  - id: step_05
    name: 点击保存
    action: click
    locator:
      primary:
        strategy: uia
        name: "保存"
        control_type: Button
      fallback:
        strategy: ocr_text
        text: "保存"
    confidence: 0.92
    checkpoint: true

  # ---- 阶段2: 从 ERP 导出数据 ----
  - id: step_10
    name: 打开ERP系统
    action: web_navigate
    params:
      url: "{{erp_url}}/report/sales"
      browser: chrome
    wait_until:
      type: web_selector_visible
      selector: "#report-filter"
      timeout: 15000
    checkpoint: true
    confidence: 0.95

  - id: step_11
    name: 选择月份
    action: web_select
    params:
      value: "{{month}}"
    locator:
      primary:
        strategy: css_selector
        selector: "#month-picker"
    confidence: 0.90

  - id: step_12
    name: 点击查询
    action: web_click
    locator:
      primary:
        strategy: css_selector
        selector: "button.search-btn"
      fallback:
        strategy: ocr_text
        text: "查询"
    wait_until:
      type: web_selector_visible
      selector: "#data-table tbody tr"
      timeout: 30000
    confidence: 0.88

  - id: step_13
    name: 点击导出
    action: web_click
    locator:
      primary:
        strategy: css_selector
        selector: "#export-btn"
      fallback:
        strategy: image_match
        template: "snapshots/step_13_export_btn.png"
        threshold: 0.85
    wait_until:
      type: file_downloaded
      pattern: "*.xlsx"
      timeout: 30000
    confidence: 0.72
    ai_assisted: true
    on_fail:
      strategy: ai_retry
      hint: "导出按钮可能在工具栏或右键菜单中"
    checkpoint: true

  # ---- 阶段3: 数据处理 ----
  - id: step_20
    name: 读取导出数据
    action: python_script
    params:
      script: |
        import openpyxl
        wb = openpyxl.load_workbook(downloaded_file)
        data = wb.active
        # 提取数据到变量
        ctx.set("sales_data", extract_sales_data(data))
    confidence: 0.98

  # ---- 阶段4: 填入模板 ----
  - id: step_30
    name: 切换到Excel窗口
    action: switch_window
    params:
      title_contains: "销售报表"
    confidence: 0.90

  - id: step_31
    name: 填入销售数据
    action: python_script
    params:
      script: |
        import win32com.client
        excel = win32com.client.GetActiveObject("Excel.Application")
        ws = excel.ActiveSheet
        for i, row in enumerate(ctx.get("sales_data")):
            for j, val in enumerate(row):
                ws.Cells(i+2, j+1).Value = val
    confidence: 0.95

  - id: step_32
    name: 保存并关闭
    action: hotkey
    params:
      keys: "ctrl+s"
    wait_until:
      type: value_stable
      timeout: 3000
    confidence: 0.95
    checkpoint: true

# ============ 错误处理策略 ============
error_handling:
  default:
    retry_count: 3
    retry_interval: 2000
    on_final_fail: ai_recovery

  strategies:
    ai_recovery:
      max_attempts: 2
      rollback_to: nearest_checkpoint
      notify_on_fail: true

    skip_and_continue:
      log_level: warning
      continue_from: next_step

# ============ 触发器（可选） ============
triggers:
  - type: schedule
    cron: "0 9 1 * *"              # 每月1号上午9点
    enabled: false
  - type: manual
    description: "手动执行"
```

## 4. 操作类型定义 (Action Types)

### 4.1 桌面操作

| action | 说明 | 必要参数 | 可选参数 |
|--------|------|---------|---------|
| `launch_app` | 启动应用 | path \| process | args, work_dir |
| `switch_window` | 切换窗口 | title_contains \| process | |
| `close_window` | 关闭窗口 | title_contains \| process | force |
| `click` | 鼠标点击 | locator | button(left/right), count |
| `double_click` | 双击 | locator | |
| `right_click` | 右键点击 | locator | |
| `type_text` | 输入文本 | text, locator | clear_first |
| `hotkey` | 快捷键 | keys | |
| `scroll` | 滚轮滚动 | direction, count | locator |
| `drag_drop` | 拖拽 | from_locator, to_locator | |
| `select_item` | 选择列表项 | value \| index, locator | |
| `get_value` | 读取控件值 | locator, save_to | |
| `set_value` | 设置控件值 | value, locator | |
| `wait_window` | 等待窗口 | title_contains | timeout |
| `screenshot` | 手动截图 | save_to | region |

### 4.2 Web 操作

| action | 说明 | 必要参数 | 可选参数 |
|--------|------|---------|---------|
| `web_navigate` | 导航到 URL | url | browser, wait_until |
| `web_click` | 点击元素 | locator | |
| `web_type` | 输入文本 | text, locator | clear_first |
| `web_select` | 下拉选择 | value, locator | |
| `web_check` | 勾选复选框 | locator | checked(bool) |
| `web_upload` | 文件上传 | file_path, locator | |
| `web_download` | 等待下载 | | pattern, timeout |
| `web_get_text` | 读取文本 | locator, save_to | |
| `web_wait` | 等待元素 | locator | state, timeout |
| `web_execute_js` | 执行 JS | script | |

### 4.3 流程控制

| action | 说明 | 参数 |
|--------|------|------|
| `condition` | 条件分支 | if, then(steps), else(steps) |
| `loop` | 循环 | type(count/while/for_each), body(steps) |
| `break` | 跳出循环 | |
| `goto` | 跳转到步骤 | target_step_id |
| `sub_workflow` | 调用子流程 | workflow_id, variables |
| `python_script` | 执行 Python | script |
| `set_variable` | 设置变量 | name, value \| expression |
| `log` | 输出日志 | message, level |
| `pause` | 暂停等待 | message（等待用户确认） |
| `assert` | 断言检查 | condition, message |

### 4.4 等待条件类型

| wait_until.type | 说明 | 参数 |
|----------------|------|------|
| `window_title_contains` | 窗口标题包含 | value, timeout |
| `window_appear` | 窗口出现 | title \| process, timeout |
| `window_disappear` | 窗口消失 | title \| process, timeout |
| `element_exist` | 控件存在 | locator, timeout |
| `element_visible` | 控件可见 | locator, timeout |
| `element_enabled` | 控件可用 | locator, timeout |
| `value_equals` | 值等于 | locator, expected, timeout |
| `value_stable` | 值稳定(不再变化) | timeout, stable_duration |
| `web_selector_visible` | Web元素可见 | selector, timeout |
| `file_downloaded` | 文件下载完成 | pattern, timeout |
| `process_started` | 进程启动 | process_name, timeout |
| `delay` | 固定等待(最后手段) | milliseconds |

## 5. 变量系统

### 5.1 变量作用域

```
全局变量 (workflow.variables)
  │  在整个流程中可用
  │
  ├── 步骤输出变量 (step.save_to)
  │    step_12 的输出可在 step_13+ 中使用
  │
  └── 内置变量 (自动可用)
       {{__date__}}          当前日期 YYYY-MM-DD
       {{__time__}}          当前时间 HH:MM:SS
       {{__timestamp__}}     Unix 时间戳
       {{__step_index__}}    当前步骤序号
       {{__workflow_name__}} 流程名称
       {{__run_id__}}        本次执行 ID
```

### 5.2 表达式求值

支持简单表达式用于条件判断和值计算：

```yaml
# 条件表达式
- action: condition
  params:
    if: "{{sales_total}} > 100000"
    then:
      - action: log
        params:
          message: "销售额超标，发送邮件通知"
    else:
      - action: log
        params:
          message: "销售额正常"

# 字符串拼接
- action: type_text
  params:
    text: "{{month}}_{{__date__}}_报表.xlsx"

# 列表遍历
- action: loop
  params:
    type: for_each
    collection: "{{sheet_names}}"
    item_var: "current_sheet"
    body:
      - action: click
        locator:
          primary:
            strategy: uia
            name: "{{current_sheet}}"
```
