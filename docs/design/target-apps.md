# 目标应用适配与技术难点

## 1. 应用分类与适配策略

### 1.1 适配优先级矩阵

```
                    控件树可获取
                    ↑
          高        │  区域A          区域B
      (FlaUI直接)   │  WinForms      WPF/UWP
                    │  Win32标准控件   .NET应用
                    │
                    │  区域C          区域D
          低        │  Java Swing     Canvas/DirectX
      (需要兜底)    │  远程桌面       自绘界面/游戏
                    │
                    └──────────────────────────►
                    低                       高
                         界面复杂度
```

| 区域 | 策略 | 难度 |
|------|------|------|
| A | FlaUI 直接操作，最理想 | ★☆☆☆☆ |
| B | FlaUI + 少量图像辅助 | ★★☆☆☆ |
| C | JAB 桥接 / OCR + 坐标 | ★★★☆☆ |
| D | 纯图像匹配 + AI 视觉 | ★★★★☆ |

## 2. Office 系列适配

### 2.1 策略：COM 接口优先，UI 操作兜底

```
Office 自动化的两条路径:

路径1: COM 接口（推荐，90%场景）
  Python → win32com.client → Excel/Word/Outlook COM API
  ├── 优点: 稳定、快速、不依赖UI状态、可操作隐藏数据
  ├── 缺点: 无法操作插件界面、宏对话框、自定义Ribbon
  └── 适用: 数据读写、格式设置、公式计算、邮件发送

路径2: UI 自动化（兜底，10%场景）
  C# → FlaUI → Excel/Word UI 控件
  ├── 优点: 能操作任何可见界面，包括插件
  ├── 缺点: 依赖窗口状态、速度慢、容易因版本更新失效
  └── 适用: 插件交互、Ribbon 自定义按钮、宏对话框
```

### 2.2 Excel 适配详情

```python
# COM 接口方式（推荐）
import win32com.client

excel = win32com.client.gencache.EnsureDispatch("Excel.Application")
excel.Visible = True  # 调试时可见

# 打开工作簿
wb = excel.Workbooks.Open(r"D:\报表\template.xlsx")
ws = wb.ActiveSheet

# 读写单元格
value = ws.Range("A1").Value
ws.Range("B2").Value = "新数据"

# 批量写入（性能优化：一次写入整个区域）
import numpy as np
data = [["产品A", 100, 200], ["产品B", 150, 300]]
ws.Range("A2:C3").Value = data

# 执行公式
ws.Range("D2").Formula = "=SUM(B2:C2)"

# 另存为
wb.SaveAs(r"D:\报表\2026-03_report.xlsx")
```

```
Excel COM 常用操作速查:
  读取值:    ws.Range("A1").Value / ws.Cells(1,1).Value
  写入值:    ws.Range("A1").Value = "xxx"
  公式:      ws.Range("A1").Formula = "=SUM(B1:B10)"
  格式:      ws.Range("A1").Font.Bold = True
  合并:      ws.Range("A1:C1").Merge()
  筛选:      ws.Range("A1").AutoFilter(Field=1, Criteria1="条件")
  排序:      ws.Range("A1:C10").Sort(Key1=ws.Range("B1"))
  复制粘贴:  ws.Range("A1:C10").Copy(ws.Range("E1"))
  图表:      ws.ChartObjects.Add(...)
  打印:      ws.PrintOut()
  保存:      wb.Save() / wb.SaveAs(path)
```

### 2.3 Word 适配

```python
# COM 接口
word = win32com.client.gencache.EnsureDispatch("Word.Application")
doc = word.Documents.Open(r"D:\docs\template.docx")

# 查找替换
find = doc.Content.Find
find.Text = "{{company_name}}"
find.Replacement.Text = "某某公司"
find.Execute(Replace=2)  # 2 = wdReplaceAll

# 表格操作
table = doc.Tables(1)
table.Cell(1, 1).Range.Text = "标题"
```

### 2.4 Outlook 适配

```python
# COM 接口
outlook = win32com.client.Dispatch("Outlook.Application")
mail = outlook.CreateItem(0)  # 0 = olMailItem
mail.To = "user@company.com"
mail.Subject = "月度报表"
mail.Body = "请查收附件中的月度销售报表。"
mail.Attachments.Add(r"D:\报表\2026-03_report.xlsx")
mail.Send()
```

### 2.5 Office UI 操作（FlaUI 兜底）

```
Office 应用的 UI 自动化注意事项:

1. Ribbon 控件
   - Office Ribbon 使用自定义控件，AutomationId 不稳定
   - 建议用 Name 属性定位（如 "保存"、"另存为"）
   - 不同版本 Office 的控件名称可能不同

2. 对话框
   - "另存为"对话框是标准 Win32 对话框，FlaUI 可直接操作
   - 文件名输入框: AutomationId = "FileNameControlHost"
   - 保存按钮: Name = "保存" 或 "Save"

3. 版本差异
   - Office 2016/2019/365 的 Ribbon 布局不同
   - 建议用 Name 而非位置定位
   - 准备多套 locator 适配不同版本
```

## 3. ERP / 财务系统适配

### 3.1 用友 U8

```
技术特点:
  - 基于 VB6 / .NET WinForms 混合架构
  - 部分控件可通过 UIAutomation 获取
  - 菜单系统使用自定义控件，FlaUI 可能无法获取
  - 表格控件（Grid）是自绘的

适配策略:
  ├── 主界面导航: FlaUI 定位菜单树
  ├── 表单填写: FlaUI 定位输入框（大部分有 Name）
  ├── 自定义菜单: OCR 识别菜单文字 + 坐标点击
  ├── 数据表格:
  │   ├── 优先尝试 FlaUI DataGrid 模式
  │   ├── 不行就用 COM 接口（U8 有 COM API）
  │   └── 最后用 OCR 读取表格内容
  └── 弹窗处理: 注册全局弹窗监听器

特殊注意:
  - U8 登录窗口有时会弹出更新提示，需要预处理
  - U8 的加密狗 / License 检测可能影响自动化
  - 建议在任务启动时先检查 U8 是否正常运行
```

### 3.2 金蝶 KIS / K3

```
技术特点:
  - KIS: 基于 VB6，控件树较差
  - K3: 基于 .NET，控件树较好
  - K3 Cloud: B/S 架构，走 Web 自动化

适配策略:
  ├── K3 Cloud (B/S): Playwright 操控浏览器
  ├── K3 Wise (.NET): FlaUI 直接操作
  ├── KIS (VB6):
  │   ├── 部分控件可用 FlaUI
  │   ├── 数据表格需要 OCR 或 COM
  │   └── 老版本可能需要 SendMessage
  └── 通用: 金蝶有 BOS 开放平台，优先用 API
```

### 3.3 SAP GUI

```
技术特点:
  - SAP GUI 有专门的 Scripting API
  - 不要用 UI 点击，用 SAP 脚本

适配策略:
  SAP GUI Scripting API（强烈推荐）:
    import win32com.client
    sap = win32com.client.GetObject("SAPGUI")
    app = sap.GetScriptingEngine
    session = app.Children(0).Children(0)

    # 输入事务码
    session.findById("wnd[0]/tbar[0]/okcd").text = "/nVA01"
    session.findById("wnd[0]").sendVKey(0)  # 回车

    # 读取字段
    value = session.findById("wnd[0]/usr/txtVBAK-VBELN").text

    # 点击按钮
    session.findById("wnd[0]/tbar[1]/btn[8]").press()

注意:
  - 需要在 SAP GUI 中启用脚本（Options → Accessibility & Scripting）
  - 部分企业会禁用 SAP 脚本，需要管理员开启
  - SAP 控件 ID 格式固定，非常稳定
```

### 3.4 B/S 架构 ERP (通用)

```
对于 Web 版 ERP（用友 NC Cloud、金蝶 Cloud、浪潮等）:

适配策略:
  ├── Playwright 操控浏览器
  ├── CSS Selector / XPath 定位元素
  ├── 对 iframe 需要切换 context
  └── 对动态加载内容需要智能等待

常见问题:
  ├── iframe 嵌套: frame = page.frame_locator("#mainFrame")
  ├── 动态ID: 不用 ID 定位，用文字/属性组合
  ├── 验证码: OCR 识别 或 接入打码平台
  ├── Session 超时: 定期检测登录态，过期自动重登
  └── 前端框架差异: React/Vue/Angular 渲染时机不同
```

## 4. 自研桌面程序适配

### 4.1 按框架分类

| UI 框架 | FlaUI 支持度 | 建议 |
|---------|-------------|------|
| WinForms | 优秀 | 直接用 FlaUI，确保控件设置了 Name/AccessibleName |
| WPF | 优秀 | 直接用 FlaUI，确保设置了 AutomationProperties.AutomationId |
| UWP | 良好 | FlaUI UIA3 模式支持 |
| Electron | 一般 | 优先用 Playwright 连接 Electron 的 Chrome 实例 |
| Qt | 一般 | Qt 5.12+ 支持 UIAutomation，老版本需要 image 兜底 |
| CEF (Chromium Embedded) | 差 | 尝试 CDP 连接，否则 image 兜底 |
| Delphi | 一般 | 标准控件可用，自绘控件需要 image |
| JavaFX | 差 | 需要 Java Access Bridge (JAB) |

### 4.2 Electron 应用专项

```
Electron 应用的两种操作方式:

方式1: Playwright 连接（推荐）
  - Electron 内嵌 Chromium，可通过 CDP 协议连接
  - 启动时加 --remote-debugging-port=9222
  - Playwright 通过 connect_over_cdp 连接

  from playwright.sync_api import sync_playwright
  pw = sync_playwright().start()
  browser = pw.chromium.connect_over_cdp("http://localhost:9222")
  page = browser.contexts[0].pages[0]
  page.click("#my-button")

方式2: FlaUI 操作外壳
  - Electron 窗口本身是 Win32 窗口
  - 可以获取窗口句柄、标题、位置
  - 内部 Web 内容无法通过 FlaUI 获取细节

建议: 优先方式1，窗口级操作用方式2 辅助
```

## 5. 通用 Windows 应用适配

### 5.1 应用探测流程

```
遇到未知应用时的自动探测:

1. 获取进程信息
   ├── 进程名、路径、版本信息
   ├── 模块列表 (判断 .NET / Java / Electron)
   └── 窗口类名 (判断 UI 框架)

2. 尝试 FlaUI 连接
   ├── 成功 → 获取控件树，评估可用性
   │   ├── 控件有 AutomationId → 标记为"优秀"
   │   ├── 控件只有 Name → 标记为"良好"
   │   └── 控件信息很少 → 标记为"一般"
   └── 失败 → 标记为"不支持UIAutomation"

3. 检测特殊运行时
   ├── 检查是否加载了 Java 相关 DLL → 尝试 JAB
   ├── 检查是否是 Electron (有 electron.exe) → 尝试 CDP
   └── 检查是否是 CEF (有 libcef.dll) → 尝试 CDP

4. 生成适配报告
   ├── 推荐的自动化策略
   ├── 可获取的控件信息质量评估
   └── 需要 image/OCR 兜底的区域
```

### 5.2 Java 应用适配 (JAB)

```
Java Access Bridge (JAB) 配置:

1. 启用 JAB
   - 运行: %JAVA_HOME%\bin\jabswitch -enable
   - 或手动: 复制 windowsaccessbridge-64.dll 到 system32

2. C# 调用 JAB
   - 使用 WindowsAccessBridgeInterop 库
   - 或直接 P/Invoke JAB 的 DLL 函数

3. 获取 Java 控件信息
   - getAccessibleContextFromHWND → 获取根节点
   - getAccessibleChildFromContext → 遍历子节点
   - getAccessibleActions → 获取可用操作
   - doAccessibleActions → 执行操作

注意:
  - JAB 需要目标 Java 应用和自动化程序的位数一致 (32/64位)
  - 部分 Java 应用使用 SWT 而非 Swing，JAB 可能无效
  - JAB 的性能不如 UIAutomation，控件树遍历较慢
```

## 6. 技术难点与解决方案

### 6.1 控件树获取失败

```
问题: 某些应用的控件无法通过 UIAutomation 获取

原因:
  - 应用使用自绘控件 (Canvas / DirectX)
  - 应用未实现 Accessibility 接口
  - 控件在 overlay / popup 层中

解决方案（按优先级）:
  1. 尝试其他 Automation 模式
     - FlaUI 支持 UIA2 和 UIA3 两种模式
     - 某些控件只在 UIA2 下可见，某些只在 UIA3 下可见

  2. Win32 消息级操作
     - FindWindow / FindWindowEx 获取句柄
     - SendMessage 发送 WM_CLICK / WM_SETTEXT
     - GetWindowText 获取文本

  3. OCR + 坐标定位
     - PaddleOCR 识别屏幕文字
     - 根据文字位置计算点击坐标

  4. 模板匹配
     - OpenCV matchTemplate
     - 录制时保存按钮/图标截图作为模板

  5. AI 视觉理解（终极方案）
     - 截图发给多模态 LLM
     - 让 AI 分析目标元素位置
     - 返回坐标执行点击
```

### 6.2 动态界面适配

```
问题: 界面布局在不同时间/用户/数据下不同

场景:
  - ERP 列表页数据量不同，目标行位置变化
  - 弹窗位置不固定
  - 控件因权限不同而隐藏/显示

解决方案:
  1. 多特征组合定位（不依赖单一定位方式）
     locator:
       primary:
         strategy: uia_combined
         conditions:
           - control_type: Button
           - name_contains: "导出"
           - is_enabled: true

  2. 相对定位（相对于稳定锚点）
     locator:
       strategy: relative
       anchor:
         name: "操作栏"
         control_type: ToolBar
       offset:
         direction: right
         index: 3  # 锚点右边第3个按钮

  3. 内容搜索（在列表/表格中找目标行）
     locator:
       strategy: table_search
       table_locator: { automation_id: "DataGrid1" }
       search_column: 1
       search_value: "{{order_id}}"
       action_column: 5  # 操作列
```

### 6.3 弹窗和异常对话框

```
问题: 回放时出现录制时没有的弹窗

解决方案: 全局弹窗监听器

实现方式:
  1. 后台线程持续监听新窗口创建
  2. 新窗口出现时检查是否是已知弹窗
  3. 按预定义规则自动处理

预定义弹窗处理规则:
  rules:
    - pattern:
        title_contains: "更新"
      action: click_button
      button_name: "稍后"

    - pattern:
        title_contains: "是否保存"
      action: click_button
      button_name: "保存"

    - pattern:
        title_contains: "错误"
        has_button: "确定"
      action: click_button
      button_name: "确定"
      then: screenshot_and_log

    - pattern:
        title_contains: "登录已过期"
      action: trigger_relogin
      then: retry_current_step

    - pattern:
        unknown: true
      action: ai_analyze
      then: decide_based_on_ai

弹窗监听器还需要处理:
  - Windows 系统通知
  - UAC 提权对话框
  - 杀毒软件弹窗
  - 输入法候选窗口（不要误判为弹窗）
```

### 6.4 性能优化

```
问题: 每步都截图 + 获取控件树导致执行缓慢

优化策略:

1. 截图优化
   ├── 使用 DXGI Desktop Duplication（硬件加速）
   ├── 只在需要时截全屏，平时只截操作区域
   ├── 截图异步写磁盘，不阻塞执行
   ├── 成功步骤的截图可延迟写入或跳过
   └── 使用 JPEG 替代 PNG（正常执行时，AI 分析时用 PNG）

2. 控件树优化
   ├── 缓存控件树，同一窗口 2 秒内不重复获取
   ├── 只获取目标控件路径上的节点，不遍历整棵树
   ├── 对已知稳定的 locator，跳过 fallback 查找
   └── 使用 TreeScope.Children 而非 TreeScope.Descendants

3. 等待优化
   ├── 用 polling 替代固定 sleep (每 200ms 检查一次)
   ├── 检测到条件满足立即继续，不等满超时
   └── 连续成功步骤间不额外等待

4. 批量操作
   ├── 连续的 Excel 写入合并为一次 COM 调用
   ├── 连续的 Web 操作在同一个 page context 中执行
   └── 变量计算在 Python 内完成，减少跨进程调用
```

### 6.5 多显示器 / DPI 适配

```
问题: 录制和回放的屏幕环境不同

差异场景:
  - 录制: 双屏 4K，DPI 150%
  - 回放: 单屏 1080p，DPI 100%

解决方案:

1. 录制时记录环境信息
   metadata:
     screens: [{width: 3840, height: 2160, dpi: 1.5, primary: true}, ...]

2. 回放时适配
   ├── 检测当前屏幕配置
   ├── 计算坐标缩放比例
   ├── 调整窗口大小以匹配录制时的比例
   └── 如果差异太大，提示用户确认

3. 优先使用 DPI 无关的定位
   ├── 控件树定位（完全不受 DPI 影响）
   ├── 相对百分比坐标（自动适配分辨率）
   └── OCR 文字定位（只要文字可见就能定位）

4. 窗口归一化
   ├── 回放前将窗口调整到录制时的大小
   ├── 移动到与录制时相同的屏幕位置
   └── 确保窗口状态一致（非最大化/最小化）
```

### 6.6 录制噪音和误操作

```
问题: 用户录制时的犹豫、误操作、无关操作

解决方案: 多层过滤 + 用户确认

第一层: 实时过滤（录制时）
  ├── 过滤鼠标移动事件（除非涉及 hover 交互）
  ├── 过滤输入法候选窗口的点击
  └── 过滤系统托盘、任务栏的操作

第二层: 智能合并（录制后处理）
  ├── 连续输入合并为一次 type_text
  ├── 操作 + 撤销 配对删除
  ├── 连续滚轮合并
  └── 短间隔重复点击去重

第三层: 意图分析（AI 辅助）
  ├── 分析操作上下文，识别无意义操作
  ├── 标记可疑步骤让用户确认
  └── 生成自然语言描述，方便用户审阅

第四层: 用户审阅
  ├── 录制完成后在设计器中展示操作列表
  ├── 每步显示截图和描述
  ├── 用户可删除、编辑、重排步骤
  └── 标记为"自动识别"和"AI补全"方便重点审阅
```
