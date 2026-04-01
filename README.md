# DeskFlow - 桌面流程自动化平台

## 产品定位

**录制驱动 + AI 兜底**的桌面 RPA 平台，先自用验证，后产品化推广。

## 核心理念

1. **录制示教** — 用户操作一遍，系统自动记录并识别大部分操作
2. **AI 补全** — 对无法自动识别的操作，由 AI 分析截图和上下文来确定
3. **流程固化** — 将录制结果固化为可编辑、可复用的流程包
4. **智能回放** — 正常执行流程，遇到异常时回退并调用 AI 跨越障碍

## 目标场景

- **Web + 桌面混合自动化** — 同一流程中既操控浏览器，也操控桌面应用
- **Office 系列** — Excel、Word、Outlook 等
- **ERP / 财务系统** — 用友、金蝶、SAP 等企业软件
- **自研桌面程序** — WinForms / WPF / Electron 应用
- **通用 Windows 应用** — 任意第三方桌面软件

## 技术栈

| 层次 | 技术 | 语言 |
|------|------|------|
| 桌面控件操作 | FlaUI + Win32 API | C# |
| Web 自动化 | Playwright | Python |
| 图像识别兜底 | OpenCV + PaddleOCR | Python |
| 进程间通信 | gRPC (原型阶段用子进程+JSON) | 通用 |
| 流程引擎 | 自研 Step Runner | Python |
| 设计器 GUI | WPF 或 Avalonia | C# |
| 数据处理 | pandas + openpyxl | Python |
| AI 增强 | LLM API (多模态) | Python |
| 流程存储 | YAML + SQLite | 通用 |

## 文档索引

| 文档 | 说明 |
|------|------|
| [技术架构](docs/architecture.md) | 整体架构、模块划分、技术选型、通信方案 |
| [录制系统](docs/recording-system.md) | 录制数据结构、三级定位策略、技术实现 |
| [流程引擎](docs/workflow-engine.md) | 操作识别、流程固化、流程包格式 |
| [回放与AI恢复](docs/playback-ai-recovery.md) | 回放状态机、AI接管、稳定点机制 |
| [目标应用适配](docs/target-apps.md) | Office/ERP专项方案、技术难点攻克 |
| [开发路线图](docs/roadmap.md) | 分阶段计划、里程碑、参考仓库 |
