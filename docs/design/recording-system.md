# 录制系统设计

## 1. 设计目标

用户操作一遍目标流程，系统在后台：
1. 捕获每一次鼠标点击、键盘输入、滚轮滚动
2. 同步获取操作目标的控件信息（控件树定位）
3. 同步截取屏幕快照（图像定位兜底）
4. 将原始数据序列化为结构化的操作序列

## 2. 录制数据结构

### 2.1 单次操作快照 (RecordEvent)

```json
{
  "event_id": "evt_20260331_102345_001",
  "timestamp": "2026-03-31T10:23:45.123",
  "event_type": "mouse_click",

  "input": {
    "mouse": {
      "button": "left",
      "action": "click",
      "screen_x": 1024,
      "screen_y": 568,
      "window_relative_x": 512,
      "window_relative_y": 300,
      "relative_x_pct": 0.45,
      "relative_y_pct": 0.62
    },
    "keyboard": null
  },

  "window": {
    "process_name": "EXCEL.EXE",
    "process_id": 12345,
    "window_title": "销售报表.xlsx - Excel",
    "window_handle": "0x001A0B3C",
    "window_rect": { "x": 0, "y": 0, "width": 1920, "height": 1080 },
    "window_class": "XLMAIN"
  },

  "control": {
    "found": true,
    "automation_id": "Cell_A1",
    "name": "A1",
    "control_type": "DataItem",
    "class_name": "EXCEL7",
    "framework": "Win32",
    "path": "/Pane/Window[销售报表]/DataGrid/DataItem[A1]",
    "bounding_rect": { "x": 980, "y": 540, "width": 88, "height": 22 },
    "value_before": "",
    "value_after": null,
    "is_enabled": true,
    "is_offscreen": false,
    "parent_chain": [
      { "control_type": "DataGrid", "name": "Sheet1" },
      { "control_type": "Window", "name": "销售报表.xlsx - Excel" },
      { "control_type": "Pane", "automation_id": "MainPane" }
    ]
  },

  "screenshot": {
    "full_screen_path": "recordings/session_001/screenshots/evt_001_full.png",
    "region_crop_path": "recordings/session_001/screenshots/evt_001_crop.png",
    "crop_rect": { "x": 900, "y": 480, "width": 248, "height": 176 }
  },

  "context": {
    "previous_events": ["evt_000", "evt_minus1"],
    "time_since_last_event_ms": 1200,
    "sequence_index": 5
  }
}
```

### 2.2 键盘输入事件

```json
{
  "event_id": "evt_20260331_102348_002",
  "timestamp": "2026-03-31T10:23:48.456",
  "event_type": "keyboard_input",

  "input": {
    "mouse": null,
    "keyboard": {
      "action": "text_input",
      "text": "2026年3月销售数据",
      "raw_keys": [],
      "modifiers": []
    }
  },

  "window": { "...同上..." },
  "control": {
    "found": true,
    "automation_id": "Cell_A1",
    "value_before": "",
    "value_after": "2026年3月销售数据",
    "...其余同上..."
  },
  "screenshot": { "...同上..." }
}
```

### 2.3 快捷键事件

```json
{
  "event_type": "keyboard_hotkey",
  "input": {
    "keyboard": {
      "action": "hotkey",
      "text": null,
      "raw_keys": ["ctrl", "c"],
      "modifiers": ["ctrl"]
    }
  }
}
```

### 2.4 滚轮事件

```json
{
  "event_type": "mouse_scroll",
  "input": {
    "mouse": {
      "button": null,
      "action": "scroll",
      "scroll_delta": -120,
      "scroll_direction": "vertical",
      "screen_x": 800,
      "screen_y": 600
    }
  }
}
```

## 3. 三级定位策略

录制时**同时采集**三种定位信息，回放时按优先级依次尝试。

### 3.1 优先级 1：控件树定位（最稳定）

```
定位方式：
  ├── AutomationId（最优）   → 唯一标识符，开发者设定
  ├── Name + ControlType    → 控件名称 + 类型组合
  ├── UIA Path              → 从根到目标的控件树路径
  └── 属性组合              → 多属性 AND 查询

技术实现：
  C# FlaUI → AutomationElement.FromPoint(x, y)
           → 获取控件所有属性
           → 构建多种定位表达式

适用场景：
  ✓ WinForms / WPF / UWP 应用
  ✓ Win32 标准控件
  ✓ 大部分 .NET 应用

不适用：
  ✗ Java Swing (需 JAB 桥接)
  ✗ Canvas 绘制的自定义界面
  ✗ 远程桌面 / VNC 内的应用
  ✗ 游戏 / DirectX 渲染界面
```

### 3.2 优先级 2：相对坐标定位（通用兜底）

```
定位方式：
  ├── 相对于窗口的百分比坐标 (x_pct, y_pct)
  ├── 相对于某个锚点控件的偏移
  └── 相对于屏幕的百分比坐标（最后手段）

计算公式：
  x_pct = (click_x - window_x) / window_width
  y_pct = (click_y - window_y) / window_height

适用场景：
  ✓ 控件树无法获取的应用
  ✓ 窗口大小固定或变化规律的场景

局限性：
  ✗ 窗口布局大幅变化时失效
  ✗ 分辨率 / DPI 差异较大时需要校准
```

### 3.3 优先级 3：图像匹配定位（AI 兜底）

```
定位方式：
  ├── 模板匹配（OpenCV matchTemplate）
  │   → 用录制时的控件截图在当前屏幕中搜索
  │   → 设置相似度阈值 (默认 0.85)
  │
  ├── OCR 文字定位
  │   → 识别屏幕上的文字
  │   → 找到目标文字的位置
  │   → 适合按钮文字、标签文字等
  │
  └── AI 视觉理解（终极兜底）
      → 截图发给多模态 LLM
      → 让 AI 分析目标元素位置
      → 最慢但最智能

适用场景：
  ✓ 所有应用（万能方案）
  ✓ Canvas / DirectX 渲染的界面
  ✓ 远程桌面内的应用

局限性：
  ✗ 速度较慢（尤其 AI 方案）
  ✗ 界面样式变化大时模板匹配失效
  ✗ OCR 对小字、特殊字体识别率下降
```

### 3.4 定位器生成规则

录制时为每个操作生成一个 `Locator` 对象：

```json
{
  "locator": {
    "primary": {
      "strategy": "uia",
      "automation_id": "btnExport",
      "control_type": "Button"
    },
    "secondary": {
      "strategy": "uia_path",
      "path": "/Window[报表系统]/Pane[ToolBar]/Button[3]"
    },
    "tertiary": {
      "strategy": "relative_coord",
      "x_pct": 0.85,
      "y_pct": 0.12,
      "anchor_window": "报表系统"
    },
    "fallback": {
      "strategy": "image_match",
      "template_image": "snapshots/step5_export_btn.png",
      "threshold": 0.85
    },
    "ocr_hint": {
      "strategy": "ocr_text",
      "text": "导出",
      "region_pct": { "x": 0.7, "y": 0.0, "w": 0.3, "h": 0.2 }
    }
  }
}
```

回放时按顺序尝试：primary → secondary → tertiary → fallback → ocr_hint，全部失败则触发 AI 恢复。

## 4. 录制技术实现

### 4.1 全局钩子 (C#)

```
核心 API：
  SetWindowsHookEx(WH_MOUSE_LL, ...)    // 低级鼠标钩子
  SetWindowsHookEx(WH_KEYBOARD_LL, ...) // 低级键盘钩子

注意事项：
  - 低级钩子在所有应用上生效，无需注入
  - 钩子回调必须在 100ms 内返回，否则系统会跳过
  - 重操作（截屏、获取控件树）必须异步执行，不阻塞钩子回调
  - 使用消息队列：钩子回调 → 入队 → 后台线程消费处理
```

### 4.2 实时控件信息获取 (C#)

```
流程：
  1. 鼠标钩子触发 → 获取屏幕坐标 (x, y)
  2. 异步调用 AutomationElement.FromPoint(x, y)
  3. 获取控件属性：AutomationId, Name, ControlType, ClassName
  4. 向上遍历获取 parent_chain
  5. 获取 BoundingRectangle (控件边界矩形)
  6. 尝试获取 Value/Text/SelectionPattern 等值

性能优化：
  - FromPoint 通常 < 50ms，可接受
  - 对于快速连续点击，可以合并请求
  - 控件树缓存：同一窗口的控件树短时间内不重复获取
  - 超时保护：单次获取超过 200ms 则跳过，标记为 control.found = false
```

### 4.3 屏幕截图 (C#)

```
两种截图方式：

1. GDI BitBlt（兼容性好）
   - 支持所有 Windows 版本
   - 性能：1920x1080 约 10-20ms
   - 缺点：无法捕获硬件加速 / DX 渲染内容

2. DXGI Desktop Duplication（高性能，推荐）
   - Windows 8+ 支持
   - 性能：1920x1080 约 2-5ms
   - 能捕获 DirectX 渲染内容
   - 缺点：实现复杂，需要处理显卡切换

截图策略：
  - 每次操作截取全屏（用于 AI 分析和调试）
  - 同时裁剪操作目标周围区域（用于模板匹配）
  - 裁剪区域：以点击坐标为中心，向外扩展 124px（可配置）
  - 截图异步存储，不阻塞录制流程
  - 使用 PNG 格式（无损，AI 分析需要清晰度）
```

### 4.4 Web 操作录制

```
方案 A：Playwright CDP 监听（推荐）
  - 通过 CDP 协议监听页面上的用户操作
  - 拦截 DOM 事件：click, input, change, submit
  - 自动生成 CSS Selector / XPath
  - 优点：能获取精确的 DOM 信息

方案 B：浏览器扩展注入
  - 开发 Chrome/Edge 扩展
  - 注入 content script 监听页面事件
  - 通过 native messaging 与 Python 通信
  - 优点：不依赖 Playwright，用户正常浏览时也能录制

建议：原型阶段用方案 A，产品化时考虑方案 B
```

## 5. 录制会话管理

### 5.1 会话目录结构

```
recordings/
└── session_20260331_102300/
    ├── metadata.json           # 会话元信息
    ├── events.jsonl            # 操作事件流（一行一事件）
    ├── screenshots/            # 截图文件
    │   ├── evt_001_full.png
    │   ├── evt_001_crop.png
    │   ├── evt_002_full.png
    │   └── ...
    └── ui_trees/               # 控件树快照（关键步骤）
        ├── evt_001_tree.json
        └── ...
```

### 5.2 会话元信息 (metadata.json)

```json
{
  "session_id": "session_20260331_102300",
  "start_time": "2026-03-31T10:23:00",
  "end_time": "2026-03-31T10:35:42",
  "duration_seconds": 762,
  "total_events": 87,
  "screen_resolution": "1920x1080",
  "dpi_scale": 1.25,
  "os_version": "Windows 11 Pro 10.0.26200",
  "involved_apps": [
    { "process": "EXCEL.EXE", "title": "销售报表.xlsx - Excel" },
    { "process": "chrome.exe", "title": "ERP系统 - Chrome" }
  ],
  "description": "每月销售报表导出流程"
}
```

### 5.3 事件流格式 (events.jsonl)

使用 JSONL（每行一个 JSON），便于流式写入和增量读取：

```
{"event_id":"evt_001","timestamp":"...","event_type":"mouse_click",...}
{"event_id":"evt_002","timestamp":"...","event_type":"keyboard_input",...}
{"event_id":"evt_003","timestamp":"...","event_type":"mouse_click",...}
```

## 6. 录制噪音处理

### 6.1 需要过滤的操作

| 噪音类型 | 识别规则 | 处理方式 |
|---------|---------|---------|
| 鼠标移动 | 非点击的鼠标移动事件 | 不录制，除非跟 hover 交互相关 |
| 犹豫点击 | 极短时间内在同一区域连续点击 | 只保留最后一次 |
| 窗口聚焦 | 点击任务栏/Alt+Tab | 记录为 "切换窗口"，不记录点击坐标 |
| 误操作+撤销 | 操作后紧跟 Ctrl+Z | 整对删除 |
| 无关操作 | 操作了录制目标外的应用 | 标记为可选，询问用户是否保留 |
| 等待/思考 | 长时间无操作 | 不记录为 sleep，分析实际等待目标 |

### 6.2 操作合并规则

| 原始序列 | 合并后 |
|---------|-------|
| click(cell) → type("a") → type("b") → type("c") | click(cell) → type("abc") |
| scroll(↓) → scroll(↓) → scroll(↓) | scroll(↓, count=3) |
| click(A) → 500ms → click(A) | double_click(A)（间隔<500ms 时） |
| ctrl_down → c → ctrl_up | hotkey("ctrl+c") |

## 7. 录制控制台 UI

```
┌─────────────────────────────────────────────────┐
│  📹 录制控制台                            ─ □ ✕  │
├─────────────────────────────────────────────────┤
│                                                 │
│  状态: ● 正在录制  (已录制 23 步)                 │
│  时长: 03:42                                    │
│  当前应用: Excel - 销售报表.xlsx                  │
│                                                 │
│  ┌─── 实时操作预览 ──────────────────────────┐   │
│  │ #21 点击 [Sheet1] 标签                    │   │
│  │ #22 在 A1 输入 "2026年3月"                │   │
│  │ #23 快捷键 Ctrl+S (保存)          ← 最新  │   │
│  └───────────────────────────────────────────┘   │
│                                                 │
│  [⏸ 暂停]  [⏹ 停止]  [🔙 撤销上一步]  [⚙ 设置]  │
│                                                 │
│  ☑ 录制 Web 操作   ☑ 自动截图                    │
│  ☑ 获取控件信息     ☐ 录制鼠标移动                │
│                                                 │
└─────────────────────────────────────────────────┘
```

功能要点：
- **置顶显示**：始终在最前面但尽量小巧不遮挡
- **暂停/恢复**：暂停后操作不被录制，适合中间处理私密信息
- **撤销**：删除最后录制的 N 步操作
- **实时预览**：用自然语言描述每一步做了什么
- **热键控制**：全局热键控制录制（如 F9 暂停/恢复，F10 停止）
