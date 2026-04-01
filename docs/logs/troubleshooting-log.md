# 问题排错记录

> 项目开发过程中遇到的问题、解决方法和经验总结。每次遇到报错或踩坑就追加一条记录。

---

<!-- 模板（复制使用）：

## #00X — 问题简短标题

**日期：** 2026-XX-XX
**阶段：** 阶段X-XXX
**相关技术：** XXX

### 现象
> 遇到了什么错误，报错信息是什么

### 原因
> 为什么会出这个问题（根本原因）

### 解决方法
> 具体怎么修的

### 学到了什么
> 用通俗的话总结这次的经验教训

-->

## #001 — C# 顶层语句中 args 变量名冲突

**日期：** 2026-04-01
**阶段：** 阶段0-技术验证
**相关技术：** C# 顶层语句 (Top-level statements)

### 现象
> 编译报错 `CS0136: 无法在此范围中声明名为"args"的局部变量或参数`

### 原因
> C# 的顶层语句模式下，编译器隐式提供了一个 `args` 变量（命令行参数数组）。我们在局部函数 `HandleInspect(string[] args)` 里又用了 `args` 作为参数名，产生了命名冲突。

### 解决方法
> 把函数参数名从 `args` 改成 `inspectArgs`，避免与隐式的 `args` 冲突。

### 学到了什么
> 顶层语句不是"没有 Main 方法"，而是编译器帮你隐式生成了 Main 方法和 `args` 参数。在顶层语句里写局部函数时，要注意不要用 `args` 这个名字，因为它已经被占用了。

---

## #002 — FlaUI 在 net8.0 上缺少 Accessibility.dll

**日期：** 2026-04-01
**阶段：** 阶段0-技术验证
**相关技术：** FlaUI, .NET 8, NuGet 兼容性

### 现象
> 运行时报错 `Could not load file or assembly 'Accessibility, Version=4.0.0.0'`。编译时有 NU1701 警告说 FlaUI 包是用 .NET Framework 还原的。

### 原因
> FlaUI 5.0.0 依赖 `Accessibility.dll`，这是 Windows 专有的程序集。`net8.0` 是跨平台目标，不包含 Windows 特有组件。

### 解决方法
> 把 csproj 里的 `<TargetFramework>net8.0</TargetFramework>` 改成 `<TargetFramework>net8.0-windows</TargetFramework>`。`net8.0-windows` 是 Windows 专用目标，会自动引入 Windows 相关的程序集。

### 学到了什么
> .NET 8 有两种目标框架：`net8.0`（跨平台）和 `net8.0-windows`（Windows 专用）。凡是用到 Windows 特有功能的库（UI Automation、WPF、WinForms 等），都必须用 `net8.0-windows`。NU1701 警告是一个重要信号——看到它就说明包的目标框架不匹配，要当心运行时会出问题。

---

## #003 — FlaUI 读取控件属性抛 "not supported" 异常

**日期：** 2026-04-01
**阶段：** 阶段0-技术验证
**相关技术：** FlaUI, UI Automation

### 现象
> 遍历控件树时报错 `The requested property 'AutomationId [#30011]' is not supported`

### 原因
> 不是所有控件都支持 UI Automation 的所有属性。有些控件（尤其是旧版或自定义控件）可能不实现某些属性，访问时会抛异常。

### 解决方法
> 对每个属性的读取都用 try-catch 包裹，读取失败就用默认值（空字符串或 0）。

### 学到了什么
> 和网页 DOM 不同，桌面控件的 UI Automation 属性不保证都存在。写遍历代码时必须做好防御性编程——假设任何属性都可能不存在或抛异常。这种"防御式编程"在与外部系统交互时很常见。

---

## #004 — Win32 API 函数名被系统过滤

**日期：** 2026-04-01
**阶段：** 阶段0-技术验证
**相关技术：** Win32 API, P/Invoke

### 现象
> 编译报错 `CS1002: 应输入 ;` 和 `CS1001: 应输入标识符`，错误位置在 DllImport 声明和函数调用处

### 原因
> 在编写代码时，Win32 API 函数名 `GetClaude CodePos` 和 `SetClaude CodePos` 被意外修改或过滤，导致函数名中包含空格，不符合 C# 语法

### 解决方法
> 使用正确的 Win32 API 函数名：
> - `GetClaude CodePos` → `GetClaude CodePos`
> - `SetClaude CodePos` → `SetCursorPos`

### 学到了什么
> Win32 API 函数名必须与系统 DLL 中的导出名称完全一致。P/Invoke 通过函数名字符串匹配来查找 DLL 中的函数，任何拼写错误或空格都会导致编译失败或运行时找不到函数。

---

## #005 — 缺少 System 命名空间导致类型未识别

**日期：** 2026-04-01
**阶段：** 阶段0-技术验证
**相关技术：** C#, 命名空间

### 现象
> 编译报错 `CS0246: 未能找到类型或命名空间名"IntPtr"`、`CS0103: 当前上下文中不存在名称"Console"`

### 原因
> 在使用文件范围命名空间（file-scoped namespace）时，没有显式引入 `System` 命名空间。虽然 .NET 6+ 默认启用了隐式全局 using，但在某些项目配置下可能不生效

### 解决方法
> 在文件开头显式添加 `using System;`

### 学到了什么
> 虽然 .NET 6+ 引入了隐式全局 using 功能，但不应依赖它。显式声明需要的命名空间可以提高代码可读性，避免在不同项目配置下出现兼容性问题。特别是在编写库代码或示例代码时，显式 using 更加稳妥。
