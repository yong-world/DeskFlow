# 技术架构设计

## 1. 整体架构

```
┌──────────────────────────────────────────────────────────────┐
│                      RPA 设计器 (GUI)                        │
│                   C# WPF / Avalonia UI                       │
│          可视化流程编排 · 录制控制台 · 调试面板 · 变量管理       │
├──────────────────────────────────────────────────────────────┤
│                       流程引擎 (Core)                         │
│                          Python                               │
│       流程加载 · Step调度 · 变量管理 · 异常处理 · AI调度        │
├────────────┬─────────────┬──────────────┬────────────────────┤
│  桌面自动化  │  Web 自动化  │  数据处理层   │     AI 能力层      │
│  C# (FlaUI) │  Py(Playwr) │  Py(pandas)  │  Py(LLM+Vision)  │
├────────────┴─────────────┴──────────────┴────────────────────┤
│                       基础设施层                               │
│       录制/钩子 · 截图服务 · 日志系统 · 配置管理 · 存储         │
└──────────────────────────────────────────────────────────────┘
```

## 2. 模块划分

### 2.1 设计器模块 (Designer) — C#

职责：
- 可视化流程编排（拖拽节点、连线、配置参数）
- 录制控制面板（开始/暂停/停止录制、实时预览）
- 流程调试器（单步执行、断点、变量查看）
- 流程包管理（导入/导出/版本管理）

关键依赖：
- WPF 或 Avalonia（跨平台考虑用 Avalonia）
- 节点编辑器控件（参考 NodeNetwork 或自研）

### 2.2 录制模块 (Recorder) — C#

职责：
- 全局鼠标/键盘钩子，捕获用户操作
- 实时获取操作目标的控件信息
- 同步截屏（全屏 + 操作区域裁剪）
- 操作序列序列化为 JSON

关键依赖：
- Win32 API (`SetWindowsHookEx`)
- FlaUI (`AutomationElement.FromPoint`)
- DXGI Desktop Duplication (高性能截屏)

### 2.3 桌面自动化模块 (DesktopAutomation) — C#

职责：
- 控件查找（按 AutomationId / Name / Path / ControlType）
- 控件操作（Click / SetValue / GetValue / Expand / Select）
- 窗口管理（FindWindow / 前置 / 最大化 / 等待窗口出现）
- Win32 消息发送（SendMessage / PostMessage）

关键依赖：
- FlaUI（核心，封装 UIAutomation）
- P/Invoke (Win32 API 调用)
- Java Access Bridge (JAB，用于 Java 应用)

### 2.4 Web 自动化模块 (WebAutomation) — Python

职责：
- 浏览器生命周期管理（启动/连接/关闭）
- 页面操作（导航/点击/输入/选择/等待）
- 网络拦截（监听请求/修改响应）
- Web 录制（CDP 事件监听 + 生成操作序列）

关键依赖：
- Playwright（核心）
- CDP 协议（高级控制）

### 2.5 流程引擎模块 (WorkflowEngine) — Python

职责：
- 加载和解析流程定义（YAML/JSON）
- 按顺序/条件/循环执行 Step
- 变量存储和表达式求值
- 错误处理和恢复策略调度
- Checkpoint 管理

### 2.6 AI 能力模块 (AIService) — Python

职责：
- 录制阶段：分析无法识别的操作步骤
- 回放阶段：异常恢复决策
- 屏幕理解：截图分析 + OCR
- 流程优化建议

关键依赖：
- LLM API（Claude / GPT，多模态能力）
- PaddleOCR / Tesseract（本地 OCR）
- OpenCV（图像匹配、模板匹配）

### 2.7 图像识别模块 (VisionService) — Python

职责：
- 模板匹配（在屏幕截图中定位目标区域）
- OCR 文字识别（定位文字元素）
- 图像差异对比（判断界面是否变化）
- 验证码识别（如需要）

关键依赖：
- OpenCV（模板匹配、图像处理）
- PaddleOCR（中文 OCR，识别率优于 Tesseract）
- Pillow（图像预处理）

## 3. Python 与 C# 通信方案

### 3.1 架构模式

```
┌───────────────────┐       gRPC / REST        ┌────────────────────┐
│                   │◄─────────────────────────►│                    │
│   Python 进程      │    双向通信，protobuf      │    C# 进程          │
│                   │    序列化                  │                    │
│  - 流程引擎        │                           │  - 设计器 GUI       │
│  - Web 自动化      │                           │  - 录制模块         │
│  - AI 服务         │                           │  - 桌面自动化       │
│  - 图像识别        │                           │  - 截图服务         │
│                   │                           │                    │
└───────────────────┘                           └────────────────────┘
```

### 3.2 分阶段实施

**第一阶段：子进程 + JSON（原型验证）**

```
Python (主进程)
  │
  ├─ subprocess.run("DesktopAgent.exe", stdin=json, stdout=json)
  │    → 发送操作指令 JSON
  │    ← 接收执行结果 JSON
  │
  └─ 简单、零依赖、调试方便
     缺点：每次调用都启动进程，延迟高
```

**第二阶段：gRPC 长连接（正式版）**

```protobuf
// rpa_service.proto

service DesktopAutomation {
  // 查找控件
  rpc FindElement (FindElementRequest) returns (FindElementResponse);
  // 执行操作
  rpc PerformAction (ActionRequest) returns (ActionResponse);
  // 获取控件树
  rpc GetUITree (UITreeRequest) returns (UITreeResponse);
  // 截屏
  rpc CaptureScreen (CaptureRequest) returns (CaptureResponse);
  // 录制事件流（服务端流式）
  rpc StartRecording (RecordRequest) returns (stream RecordEvent);
}

service WorkflowEngine {
  // 执行流程
  rpc RunWorkflow (WorkflowRequest) returns (stream StepResult);
  // 暂停/恢复
  rpc PauseWorkflow (PauseRequest) returns (PauseResponse);
}
```

优点：
- 长连接，延迟低
- 强类型，接口清晰
- 支持双向流（录制事件实时推送）

**第三阶段（可选）：pythonnet 直接调用**

```python
import clr
clr.AddReference("DesktopAutomation.dll")
from DesktopAutomation import UIAgent

agent = UIAgent()
element = agent.FindElement("AutomationId", "btnExport")
element.Click()
```

优点：零网络开销、调用最快
缺点：Python 和 C# 进程耦合、调试复杂

### 3.3 通信协议选型建议

| 阶段 | 方案 | 适用场景 |
|------|------|---------|
| 原型 | 子进程 + JSON | 快速验证核心逻辑，不追求性能 |
| 正式 | gRPC | 生产环境，高频调用，流式录制 |
| 优化 | pythonnet | 对延迟极度敏感的场景（可选） |

## 4. 数据流

### 4.1 录制流程

```
用户操作 → Win32 Hook(C#) → 操作事件
                              │
                    ┌─────────┼─────────┐
                    ▼         ▼         ▼
              控件信息     屏幕截图    键盘输入
              (FlaUI)    (DXGI)     (Hook)
                    │         │         │
                    └─────────┼─────────┘
                              ▼
                     gRPC 推送到 Python
                              │
                              ▼
                    操作序列 JSON 存储
                              │
                              ▼
                    自动识别 + AI 补全
                              │
                              ▼
                    固化为流程包 (YAML)
```

### 4.2 回放流程

```
加载流程 YAML
    │
    ▼
解析 Step 列表
    │
    ▼
┌─────────────────────────────┐
│ 对每个 Step:                 │
│  1. 评估前置条件/等待条件      │
│  2. 选择定位策略              │
│     → 优先控件树 (C# gRPC)   │
│     → 退而求其次用图像匹配    │
│  3. 执行操作                 │
│  4. 验证操作结果              │
│  5. 成功 → 下一步            │
│     失败 → 重试/AI恢复       │
└─────────────────────────────┘
```

## 5. 目录结构规划

```
DeskFlow/
├── README.md                    # 项目总览
├── docs/                        # 设计文档
│   ├── architecture.md          # 本文档
│   ├── recording-system.md      # 录制系统设计
│   ├── workflow-engine.md       # 流程引擎设计
│   ├── playback-ai-recovery.md  # 回放与AI恢复
│   ├── target-apps.md           # 目标应用适配
│   └── roadmap.md               # 开发路线图
│
├── proto/                       # gRPC 协议定义
│   └── rpa_service.proto
│
├── python/                      # Python 端
│   ├── engine/                  # 流程引擎
│   │   ├── runner.py            # Step 执行器
│   │   ├── scheduler.py         # 任务调度
│   │   ├── variables.py         # 变量管理
│   │   └── checkpoint.py        # 稳定点管理
│   ├── web/                     # Web 自动化
│   │   ├── browser.py           # 浏览器管理
│   │   ├── actions.py           # 页面操作
│   │   └── recorder.py          # Web 录制
│   ├── ai/                      # AI 服务
│   │   ├── analyzer.py          # 操作分析
│   │   ├── recovery.py          # 异常恢复
│   │   └── prompts.py           # Prompt 模板
│   ├── vision/                  # 图像识别
│   │   ├── ocr.py               # OCR 服务
│   │   ├── template_match.py    # 模板匹配
│   │   └── diff.py              # 图像对比
│   ├── grpc_client/             # gRPC 客户端
│   │   └── desktop_client.py
│   └── utils/                   # 工具函数
│       ├── screenshot.py
│       └── logger.py
│
├── csharp/                      # C# 端
│   ├── DesktopAgent/            # 桌面自动化服务
│   │   ├── Automation/          # FlaUI 封装
│   │   ├── Hooks/               # 键鼠钩子
│   │   ├── Capture/             # 截屏服务
│   │   └── GrpcServer/          # gRPC 服务端
│   └── Designer/                # 设计器 GUI
│       ├── Views/               # WPF 视图
│       ├── ViewModels/          # MVVM
│       └── Controls/            # 自定义控件(节点编辑器等)
│
├── workflows/                   # 流程包存储
│   └── examples/                # 示例流程
│
└── tests/                       # 测试
    ├── python/
    └── csharp/
```
