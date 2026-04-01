# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DeskFlow — Desktop RPA (Robotic Process Automation) platform with "recording-driven + AI fallback" approach for automating desktop and web workflows on Windows. Monorepo with C# (.NET 8) and Python (uv) in a single repository.

**Core idea:** User demonstrates a workflow once (recording), the system captures and recognizes operations, solidifies them into reusable workflow packages, and replays them with AI-powered recovery when things go wrong.

## Architecture

**Dual-language, dual-process architecture:**

- **C# process** — Desktop automation (FlaUI + Win32 API), recording hooks (`SetWindowsHookEx`), screen capture (DXGI), GUI designer (WPF/Avalonia), gRPC server
- **Python process** — Workflow engine, Web automation (Playwright), AI services (multimodal LLM), vision/OCR (OpenCV + PaddleOCR), data processing (pandas/openpyxl), gRPC client

**Communication:** Phased approach — subprocess+JSON for prototyping, gRPC for production, pythonnet as optional optimization.

## Key Design Concepts

- **Three-tier locator strategy:** UI Automation (AutomationId/Name/Path) > relative coordinates > image matching (OpenCV template match / OCR / AI vision). Playback tries each in priority order.
- **Checkpoint (stable point) mechanism:** Safe-to-restart positions (app launch, page navigation, save operations). Used for rollback during AI recovery.
- **Seven-stage operation recognition pipeline:** Preprocessing > semantic recognition > locator generation > wait condition inference > variable extraction > AI completion > checkpoint marking.
- **Playback state machine:** IDLE > RUNNING > RETRYING > RECOVERING (AI) > BLOCKED (human intervention). Normal retries first, then AI takeover, then manual.
- **Confidence scoring:** Each recorded step gets a 0-1 confidence score. Steps below 0.7 are sent to multimodal LLM for AI-assisted analysis.

## Project Structure

```
├── csharp/                          # C# 端
│   ├── DeskFlow.sln                 # 解决方案
│   ├── src/DesktopAgent/            # 桌面自动化服务（控制台应用）
│   └── tests/DesktopAgent.Tests/    # xUnit 测试
├── python/                          # Python 端
│   ├── pyproject.toml               # uv 项目配置
│   ├── src/rpa/                     # 源码包
│   │   ├── engine/                  # 流程引擎
│   │   ├── web/                     # Web 自动化 (Playwright)
│   │   ├── ai/                      # AI 服务 (LLM)
│   │   └── vision/                  # OCR + 图像匹配
│   └── tests/                       # pytest 测试
├── proto/                           # gRPC 协议定义
│   └── rpa_service.proto
├── docs/                            # 设计文档
└── .github/workflows/ci.yml         # GitHub Actions CI
```

## Workflow Package Format

- **`manifest.json`** — Package metadata, requirements, variable definitions, statistics
- **`workflow.yaml`** — Step definitions with actions, locators, wait conditions, checkpoints
- **`snapshots/`** — Screenshots for image matching fallback
- **`scripts/`** — Custom Python scripts for advanced steps

Variables use `{{variable_name}}` template syntax. Built-in variables: `__date__`, `__time__`, `__timestamp__`, `__step_index__`, `__run_id__`.

## Target Application Strategies

- **Office:** COM interface preferred (win32com), FlaUI for UI-only operations (Ribbon, dialogs)
- **SAP:** SAP GUI Scripting API (not UI clicks)
- **ERP (desktop):** FlaUI + OCR fallback for custom controls (e.g., Yonyou U8 menus)
- **ERP (web/B/S):** Playwright
- **Electron apps:** Playwright via CDP (`connect_over_cdp`), FlaUI for window-level operations
- **Java apps:** Java Access Bridge (JAB)

## Development Phases

0. **Tech Spike** — Validate FlaUI, hooks, DXGI, Playwright, Python-C# IPC, OCR, LLM vision
1. **Recording & Playback Prototype** — Hooks, control info capture, screenshots, basic replay
2. **Workflow Engine & Solidification** — Recognition pipeline, YAML workflow format, variables, conditions/loops
3. **AI Integration** — AI completion for low-confidence steps, AI recovery, OCR/image matching, popup handler
4. **Visual Designer** — WPF/Avalonia GUI, node-based editing, debugger, control picker
5. **Productization** — Installer, auto-update, scheduling, notifications, documentation

## Build & Test Commands

```bash
# C# — build and test
cd csharp
dotnet build
dotnet test

# Python — install deps and test
cd python
uv sync --dev
uv run pytest

# Run a single C# test
dotnet test csharp --filter "FullyQualifiedName~TestMethodName"

# Run a single Python test
cd python && uv run pytest tests/test_sample.py::test_placeholder
```

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs on push/PR to `main`:
- **C# job** (windows-latest): `dotnet restore` → `dotnet build` → `dotnet test`
- **Python job** (ubuntu-latest): `uv sync --dev` → `uv run pytest`

## Documentation Index

**Design documents** (`docs/design/`):
- `architecture.md` — Overall architecture, module breakdown, C#-Python communication
- `recording-system.md` — RecordEvent data structure, three-tier locator, hook implementation, noise filtering
- `workflow-engine.md` — Recognition pipeline, workflow.yaml format, action types, variable system
- `playback-ai-recovery.md` — Playback state machine, retry/checkpoint/AI recovery, execution logging
- `target-apps.md` — Per-application adaptation strategies, technical challenges
- `roadmap.md` — Phased plan, milestones, reference repos, learning path

**Log documents** (`docs/logs/`):
- `session-plan.md` — Pre-session plans (goals, approach, task checklist, expected output)
- `dev-log.md` — Development session records (what was done, what was learned)
- `test-log.md` — Test execution records (test steps, results, issues found)
- `troubleshooting-log.md` — Problem-solving records (errors encountered, solutions)
- `progress.md` — Current project status and completed milestones
