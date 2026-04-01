# 开发路线图与参考资源

## 1. 分阶段开发计划

### 阶段 0: 技术验证 (Tech Spike)

**目标：** 验证核心技术可行性，跑通最小链路

```
最小链路：录制一个简单操作 → 回放成功

验证项:
  ☐ C# FlaUI 能否获取目标应用的控件树
  ☐ Win32 Hook 能否稳定捕获鼠标键盘事件
  ☐ DXGI 截屏能否正常工作
  ☐ Python Playwright 能否操控浏览器
  ☐ Python ↔ C# 子进程通信是否可用
  ☐ PaddleOCR 中文识别率是否满足需求
  ☐ LLM API 多模态能否分析屏幕截图

交付物:
  - 一个 C# 控制台程序: 获取鼠标下的控件信息 + 截屏
  - 一个 Python 脚本: 调用 C# 程序 + Playwright 操控浏览器
  - 验证报告: 哪些目标应用可以 FlaUI 直接操作，哪些需要兜底
```

### 阶段 1: 录制与回放原型

**目标：** 能录制简单流程并成功回放

```
功能范围:
  ☐ 全局鼠标/键盘钩子 (C#)
  ☐ 实时控件信息获取 (C# FlaUI)
  ☐ 自动截屏 (C#)
  ☐ 操作事件序列化为 JSONL (C#)
  ☐ 录制控制：开始/暂停/停止 (C# 命令行或简单GUI)
  ☐ 基础回放引擎：逐步执行录制的操作 (Python)
  ☐ 控件树定位回放 (Python → C# gRPC/子进程)
  ☐ 坐标定位回放兜底
  ☐ 简单重试机制

测试场景:
  - 录制: 打开记事本 → 输入文字 → 保存
  - 录制: 打开 Excel → 在单元格输入数据 → 保存
  - 回放以上流程并验证结果

交付物:
  - 可工作的录制器 (C# 命令行)
  - 可工作的回放器 (Python 命令行)
  - 通信协议定义 (proto 或 JSON schema)
```

### 阶段 2: 流程引擎与固化

**目标：** 录制结果能智能转化为可编辑的流程包

```
功能范围:
  ☐ 操作识别管线（噪音过滤、操作合并、语义识别）
  ☐ 定位器自动生成（多级 fallback）
  ☐ 等待条件自动推断
  ☐ 变量提取（参数化硬编码值）
  ☐ 流程包格式定义 (workflow.yaml)
  ☐ 流程包导入/导出
  ☐ 流程引擎：支持顺序、条件、循环
  ☐ 变量系统（全局变量、步骤间传递）
  ☐ Checkpoint 稳定点自动标记

测试场景:
  - 录制一个包含 Web + 桌面的混合流程
  - 自动转化为 workflow.yaml
  - 修改变量后重新回放成功

交付物:
  - 操作识别管线 (Python)
  - 流程引擎 (Python)
  - workflow.yaml 格式规范
```

### 阶段 3: AI 能力集成

**目标：** AI 辅助录制识别 + 回放异常恢复

```
功能范围:
  ☐ AI 补全：低置信度步骤的分析
  ☐ AI 恢复：回放失败时的智能恢复
  ☐ 回退机制：回退到 Checkpoint 重新执行
  ☐ OCR 定位：PaddleOCR 文字定位
  ☐ 模板匹配：OpenCV 图像定位
  ☐ 恢复知识库：保存成功的恢复方案
  ☐ 全局弹窗监听器

测试场景:
  - 修改目标应用的按钮位置，AI 自动找到新位置
  - 目标应用弹出未预期的对话框，系统自动处理
  - 在控件树不可用的应用上，用 OCR/图像匹配完成操作

交付物:
  - AI 分析服务 (Python)
  - AI 恢复引擎 (Python)
  - OCR + 模板匹配服务 (Python)
  - 弹窗监听器 (C#)
```

### 阶段 4: 可视化设计器

**目标：** 提供 GUI 界面，让非技术用户也能使用

```
功能范围:
  ☐ 流程设计器 GUI (WPF / Avalonia)
  ☐ 节点式拖拽编排
  ☐ 录制控制面板（集成到 GUI）
  ☐ 流程调试器（单步执行、断点、变量查看）
  ☐ 属性面板（编辑步骤参数）
  ☐ 控件选择器（鼠标悬停高亮目标控件）
  ☐ 执行日志面板
  ☐ 流程包管理

交付物:
  - 桌面 GUI 应用
  - 用户操作手册
```

### 阶段 5: 产品化

**目标：** 可对外发布的产品

```
功能范围:
  ☐ 安装包制作
  ☐ 自动更新机制
  ☐ 多流程管理 + 定时任务
  ☐ 执行报告 + 通知（邮件/企微/钉钉）
  ☐ 多机部署 + 远程管理（可选）
  ☐ 用户账号 + 权限管理（可选）
  ☐ 流程市场/模板分享（可选）
  ☐ 文档 + 教程
  ☐ 异常监控 + 日志收集

交付物:
  - 安装包
  - 用户手册
  - API 文档
```

## 2. 技术里程碑

```
阶段 0 ────────────────────────── 技术可行性确认
  │  C# FlaUI 验证 ✓
  │  Python ↔ C# 通信 ✓
  │  OCR 识别率测试 ✓
  ▼
阶段 1 ────────────────────────── 录制回放跑通
  │  能录制简单操作并成功回放
  │  自用解决第一个实际问题
  ▼
阶段 2 ────────────────────────── 流程引擎可用
  │  能处理复杂流程（条件、循环、变量）
  │  Web + 桌面混合流程跑通
  ▼
阶段 3 ────────────────────────── AI 加持
  │  异常恢复可用
  │  控件树不可用的应用也能操作
  ▼
阶段 4 ────────────────────────── GUI 可用
  │  非技术用户可以使用
  │  内部推广
  ▼
阶段 5 ────────────────────────── 产品发布
     安装包 + 文档 + 对外推广
```

## 3. 参考仓库索引

### 3.1 核心参考

| 仓库 | 语言 | 参考价值 | 重点关注 |
|------|------|---------|---------|
| [FlaUI/FlaUI](https://github.com/FlaUI/FlaUI) | C# | 桌面控件操作 | UIAutomation 封装、控件查找模式、截屏 |
| [open-rpa/openrpa](https://github.com/open-rpa/openrpa) | C# | 整体架构 | 流程设计器、录制器、活动节点设计 |
| [robocorp/rpaframework](https://github.com/robocorp/rpaframework) | Python | Python RPA 库设计 | 模块化、桌面/Web 操作抽象、错误处理 |
| [OpenAdaptAI/OpenAdapt](https://github.com/OpenAdaptAI/OpenAdapt) | Python | AI + 录制 | 屏幕录制、AI 分析操作、模型集成方式 |

### 3.2 录制与钩子

| 仓库 | 参考价值 |
|------|---------|
| [FlaUI/FlaUI](https://github.com/FlaUI/FlaUI) | AutomationElement.FromPoint() 的使用方式 |
| [tebelorg/rpa-python](https://github.com/tebelorg/rpa-python) | 极简录制回放实现，理解最小可用设计 |
| [OpenAdaptAI/OpenAdapt](https://github.com/OpenAdaptAI/OpenAdapt) | 完整的录制管线：钩子 → 截屏 → AI 分析 |

### 3.3 流程引擎

| 仓库 | 参考价值 |
|------|---------|
| [open-rpa/openrpa](https://github.com/open-rpa/openrpa) | Workflow 引擎设计、Activity 节点模型 |
| [robocorp/rpaframework](https://github.com/robocorp/rpaframework) | Python 操作抽象、关键词驱动模式 |
| [n8n-io/n8n](https://github.com/n8n-io/n8n) | (非RPA) 节点式工作流引擎设计，可视化编排参考 |

### 3.4 AI + 视觉

| 仓库 | 参考价值 |
|------|---------|
| [OpenAdaptAI/OpenAdapt](https://github.com/OpenAdaptAI/OpenAdapt) | 多模态 LLM 分析屏幕截图的 Prompt 设计 |
| [PaddlePaddle/PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) | 中文 OCR 引擎，PP-OCRv4 模型 |
| [iflytek/astron-rpa](https://github.com/iflytek/astron-rpa) | AI Agent 与 RPA 结合的方式 |

### 3.5 设计器 / GUI

| 仓库 | 参考价值 |
|------|---------|
| [open-rpa/openrpa](https://github.com/open-rpa/openrpa) | WPF 流程设计器实现 |
| [Wouterdek/NodeNetwork](https://github.com/Wouterdek/NodeNetwork) | WPF 节点编辑器控件 |
| [AvaloniaUI/Avalonia](https://github.com/AvaloniaUI/Avalonia) | 跨平台 .NET UI 框架（WPF 替代） |
| [wyfish/RPAStudio](https://github.com/wyfish/RPAStudio) | 中文 RPA 设计器参考 |

### 3.6 通信与基础设施

| 仓库 | 参考价值 |
|------|---------|
| [grpc/grpc-dotnet](https://github.com/grpc/grpc-dotnet) | .NET gRPC 实现 |
| [grpc/grpc](https://github.com/grpc/grpc) | gRPC Python 实现 |
| [pythonnet/pythonnet](https://github.com/pythonnet/pythonnet) | Python 直接调用 .NET (备选方案) |

## 4. 技术学习路径

### 4.1 必须掌握的技术

```
C# 端:
  ├── FlaUI 库使用
  │   ├── 控件查找模式 (ConditionFactory)
  │   ├── 控件操作 (Patterns)
  │   └── 控件树遍历
  ├── Win32 API
  │   ├── SetWindowsHookEx (鼠标/键盘钩子)
  │   ├── FindWindow / GetWindowRect
  │   └── SendMessage / PostMessage
  ├── DXGI Desktop Duplication (截屏)
  └── gRPC 服务端 (Grpc.AspNetCore)

Python 端:
  ├── Playwright (Web 自动化)
  │   ├── 浏览器管理
  │   ├── 页面操作
  │   └── CDP 协议
  ├── win32com (Office COM)
  ├── OpenCV (图像处理)
  │   ├── matchTemplate (模板匹配)
  │   └── 图像预处理
  ├── PaddleOCR (文字识别)
  ├── LLM API 调用 (多模态)
  └── gRPC 客户端 (grpcio)
```

### 4.2 推荐学习顺序

```
第一周: FlaUI + Win32 Hook
  → 写一个能获取鼠标下控件信息的工具
  → 目标: 鼠标移到任意控件上，显示控件信息

第二周: Playwright + 截屏
  → 用 Playwright 自动化一个网页操作
  → 用 DXGI/GDI 实现实时截屏

第三周: Python ↔ C# 通信
  → 跑通子进程 + JSON 通信
  → 尝试 gRPC 双向通信

第四周: OCR + 模板匹配
  → 用 PaddleOCR 识别屏幕文字
  → 用 OpenCV 在截图中定位按钮

后续: 整合以上能力，开始阶段1开发
```

## 5. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 目标应用控件树完全不可用 | 核心功能受限 | OCR + 图像匹配 + AI 视觉多重兜底 |
| LLM API 响应延迟高 | AI 恢复耗时长 | 本地知识库缓存常见方案，先查本地再调 API |
| Python ↔ C# 通信不稳定 | 操作失败 | 心跳检测 + 自动重连 + 进程守护 |
| Office/ERP 版本升级导致 locator 失效 | 流程中断 | 多级定位器 + AI 自动修复 + 版本检测 |
| 录制噪音太多 | 生成的流程不可用 | 多层过滤 + AI 清洗 + 用户审阅 |
| 截屏性能不足 | 录制丢帧 | DXGI 硬件加速 + 异步写盘 + 降频采样 |
