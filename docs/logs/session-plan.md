# 开发会话计划

> 每次开发会话开始前的计划记录。记录本次要做什么、为什么做、怎么做、预期产出。

---

<!-- 模板（复制使用）：

## Session #00X — 2026-XX-XX

**阶段：** 阶段X-XXX
**预计时长：** X小时
**优先级：** 高/中/低

### 本次目标
> 用一句话说明这次会话要完成什么

### 背景与动机
> 为什么要做这个？解决什么问题？前置条件是什么？

### 技术方案
> 打算怎么实现？用什么技术？关键步骤是什么？

### 任务清单
- [ ] 任务1：具体描述
- [ ] 任务2：具体描述
- [ ] 任务3：具体描述

### 预期产出
> 这次会话结束后应该有哪些可交付成果？

**代码：**
- 文件路径1 — 功能描述
- 文件路径2 — 功能描述

**文档：**
- 更新的文档或新增的文档

**测试：**
- 需要验证的测试场景

### 风险与备选方案
> 可能遇到什么问题？如果遇到了怎么办？

| 风险 | 影响 | 备选方案 |
|------|------|---------|
| 风险描述 | 影响范围 | 如何应对 |

### 参考资料
> 本次开发需要参考的文档、代码、链接

---

-->

## Session #001 — 2026-04-01

**阶段：** 阶段0-技术验证
**预计时长：** 2小时
**优先级：** 高

### 本次目标
> 验证 Python ↔ C# 子进程通信和 FlaUI 控件树获取

### 背景与动机
> 项目刚启动，需要验证核心技术可行性。录制回放的基础是能获取桌面应用的控件信息，Python 作为主引擎需要能调用 C# 的 FlaUI 能力。

### 技术方案
1. C# 端用 FlaUI.UIA3 获取控件树，输出 JSON 到 stdout
2. Python 端用 subprocess 启动 C# 程序，解析 JSON
3. 用记事本作为测试目标应用

### 任务清单
- [x] C# 项目添加 FlaUI.UIA3 依赖
- [x] 实现 `inspect` 命令：按窗口名/进程名查找
- [x] 递归遍历控件树并序列化为 JSON
- [x] Python 封装 DesktopAgent 类
- [x] 编写端到端验证脚本
- [x] 测试并记录结果

### 预期产出

**代码：**
- `csharp/src/DesktopAgent/Program.cs` — FlaUI 控件树获取
- `python/src/rpa/desktop/__init__.py` — DesktopAgent 封装
- `python/examples/test_inspect.py` — 验证脚本

**文档：**
- `docs/logs/dev-log.md` — 记录本次开发成果
- `docs/logs/test-log.md` — 记录测试结果
- `docs/logs/troubleshooting-log.md` — 记录遇到的问题

**测试：**
- 成功获取记事本的完整控件树

### 风险与备选方案

| 风险 | 影响 | 备选方案 |
|------|------|---------|
| FlaUI 无法获取某些应用的控件树 | 核心功能受限 | 先验证常见应用（记事本、Excel），不行就用 OCR 兜底 |
| subprocess 通信不稳定 | 操作失败 | 后续改用 gRPC，当前阶段先跑通 |
| 中文乱码 | 输出不可读 | 强制 UTF-8 编码 |

### 参考资料
- FlaUI 文档：https://github.com/FlaUI/FlaUI
- Python subprocess 文档：https://docs.python.org/3/library/subprocess.html
- `docs/design/architecture.md` — 架构设计
- `docs/design/roadmap.md` — 阶段0验证项

---

## Session #002 — 2026-04-01

**阶段：** 阶段0-技术验证
**预计时长：** 1小时
**优先级：** 中

### 本次目标
> 创建键鼠操作性能测试框架，验证 Win32 SendInput API 的回放性能

### 背景与动机
> 在开始实现录制回放功能前，需要先验证键鼠模拟操作的性能指标（延迟、准确性、吞吐量），为后续优化提供基准数据。这是一个独立的测试项目，不应与主项目代码混合。

### 技术方案
1. C# 端使用 Win32 API SendInput 模拟键鼠操作
2. 接收 JSON 格式的命令（mouse_move, left_click, right_click, type_key）
3. 记录每个操作的执行时间并返回结果
4. Python 端编排测试用例，收集性能数据并生成报告

### 任务清单
- [x] 创建独立测试目录 `test/performance/`
- [x] C# 项目：MouseKeySimulator（Win32 SendInput 封装）
- [x] 实现鼠标移动、点击、键盘输入功能
- [x] Python 测试脚本：鼠标移动准确性、点击吞吐量、键盘输入性能
- [x] 运行测试并生成性能报告

### 预期产出

**代码：**
- `test/performance/csharp/MouseKeySimulator/` — C# 键鼠模拟器
- `test/performance/python/test_playback_performance.py` — Python 性能测试脚本
- `test/performance/README.md` — 测试说明文档

**文档：**
- 更新 `docs/logs/dev-log.md`
- 更新 `docs/logs/test-log.md`
- 更新 `docs/logs/progress.md`

**测试：**
- 鼠标移动准确性测试（100次迭代）
- 点击吞吐量测试（100次迭代）
- 键盘输入性能测试（50次迭代）

### 风险与备选方案

| 风险 | 影响 | 备选方案 |
|------|------|---------|
| SendInput 在某些应用中被拦截 | 回放失败 | 后续测试不同应用的兼容性，必要时使用驱动级模拟 |
| 性能不满足需求 | 回放速度慢 | 优化进程间通信方式，考虑批量发送命令 |

### 参考资料
- Win32 SendInput API 文档
- `docs/design/roadmap.md` — 阶段0验证项
