# 开发报告

> 每次开发会话的成果记录。记录做了什么、遇到了什么、学到了什么。

---

## #001 — FlaUI 控件获取 + Python↔C# 子进程通信

**日期：** 2026-04-01
**阶段：** 阶段0-技术验证
**目标：** 验证 C# FlaUI 能否获取桌面应用控件树，Python 能否通过子进程拿到结果

### 做了什么

1. **C# 端（`csharp/src/DesktopAgent/Program.cs`）**
   - 添加 FlaUI.UIA3 NuGet 包
   - 实现 `inspect` 命令：支持按窗口标题（`--name`）或进程名（`--process`）查找窗口
   - 递归遍历控件树，输出 JSON 到 stdout
   - 目标框架从 `net8.0` 改为 `net8.0-windows`

2. **Python 端（`python/src/rpa/desktop/__init__.py`）**
   - 创建 `DesktopAgent` 类，封装子进程调用
   - 自动检测 C# exe 路径
   - `inspect()` 方法：调用 C# 程序、解析 JSON、错误处理

3. **验证脚本（`python/examples/test_inspect.py`）**
   - 端到端测试：Python → C# → FlaUI → 记事本控件树 → JSON → Python 解析展示

### 验证结果

成功获取记事本的完整控件树，包括：
- 窗口标题、菜单栏（文件/编辑/查看）
- 文本编辑器区域、标签页
- 标题栏按钮（最小化/最大化/关闭）
- 状态栏（行号、字符数、编码信息）

### 遇到的问题

| # | 问题 | 解决方法 |
|---|---|---|
| 001 | C# 顶层语句 `args` 变量名冲突 | 重命名函数参数 |
| 002 | `net8.0` 缺少 Accessibility.dll | 改用 `net8.0-windows` 目标框架 |
| 003 | 部分控件属性读取抛异常 | 每个属性用 try-catch 防御 |

详见 [排错日志](troubleshooting-log.md)

### 学到的技术

- **FlaUI**：Windows UI Automation 的 C# 封装，桌面控件树类似网页的 DOM 树
- **subprocess**：Python 启动外部程序并读取输出，最简单的跨语言通信方式
- **net8.0-windows**：用到 Windows 专有功能时必须用这个目标框架
- **防御式编程**：和外部系统交互时，假设任何调用都可能失败

### 完成的进度项

- [x] C# FlaUI 能否获取目标应用的控件树
- [x] Python ↔ C# 子进程通信是否可用

---

## #002 — 键鼠操作性能测试框架

**日期：** 2026-04-01
**阶段：** 阶段0-技术验证
**目标：** 创建独立的键鼠回放性能测试框架，验证 Win32 SendInput API 的性能指标

### 做了什么

1. **项目结构**
   - 创建独立测试目录 `test/performance/`（与主项目代码分离）
   - C# 项目：`MouseKeySimulator`（.NET 8.0 Windows）
   - Python 测试脚本：`test_playback_performance.py`

2. **C# 键鼠模拟器（`test/performance/csharp/MouseKeySimulator/`）**
   - `InputSimulator.cs`：封装 Win32 API（SetCursorPos, GetClaude CodePos, SendInput）
   - 实现功能：
     - `MoveMouse(x, y)` — 鼠标移动
     - `LeftClick()` / `RightClick()` — 鼠标点击
     - `TypeKey(virtualKeyCode)` — 键盘输入
     - `GetMousePosition()` — 获取当前鼠标位置
   - `Program.cs`：命令行入口，接收 JSON 命令，返回执行结果和耗时

3. **Python 性能测试脚本（`test/performance/python/`）**
   - `test_playback_performance.py`：
     - 通过 subprocess 调用 C# 程序
     - 三个测试场景：
       1. 鼠标移动准确性（100次迭代）
       2. 点击吞吐量（100次迭代）
       3. 键盘输入性能（50次迭代）
     - 收集性能数据并生成 JSON 报告

### 测试结果

**鼠标移动准确性**（100次迭代）
- 平均位置误差：0 像素（完美准确）
- 平均延迟：0.62 ms
- 最小延迟：0.55 ms
- 最大延迟：1.08 ms

**点击吞吐量**（100次迭代）
- 总耗时：5.53 秒
- 吞吐量：18.09 次点击/秒
- 平均延迟：2.99 ms
- 标准差：2.34 ms

**键盘输入**（50次迭代）
- 平均延迟：1.31 ms
- 最小延迟：1.16 ms
- 最大延迟：1.91 ms

### 遇到的问题

| # | 问题 | 解决方法 |
|---|---|---|
| 001 | Win32 API 函数名被系统过滤 | 使用正确的函数名 SetCursorPos/GetClaude CodePos |
| 002 | 缺少 System 命名空间导致编译错误 | 添加 `using System;` |
| 003 | IntPtr 类型未识别 | 添加 System 命名空间引用 |

### 学到的技术

- **Win32 SendInput API**：Windows 底层键鼠模拟，性能优秀（亚毫秒级延迟）
- **INPUT 结构体**：使用 StructLayout 和 FieldOffset 实现 C# 与 Win32 的互操作
- **性能基准测试**：建立性能基线，为后续优化提供参考
- **C# + Python 混合架构**：C# 负责底层操作，Python 负责测试编排和数据分析

### 性能分析

1. **鼠标移动**：0.62ms 平均延迟，完全满足实时回放需求
2. **点击操作**：18 次/秒的吞吐量，对于 RPA 场景足够（通常需要等待应用响应）
3. **键盘输入**：1.31ms 延迟，可以流畅输入文本

### 完成的进度项

- [x] Win32 SendInput 键鼠模拟验证
- [x] 性能基准测试框架搭建
