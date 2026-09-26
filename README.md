# SMEbuddy 工作台

> AI 智能体桌面工作台 —— 一句话下达任务，AI 专家自主规划、调用工具（联网搜索 / 文件生成）、流式展示执行过程，并交付 Markdown / Word / PPT 等可验收产物。

基于 **Electron + React + FastAPI** 的本地桌面应用：数据（对话、配置、API Key）全部保存在本机，不上传任何服务器。

## ✨ 功能特性

- **对话式任务台**：多轮对话、流式输出、计划/思考/工具调用过程实时可见、可随时中断
- **专家 Agent 广场**：内置 12+ 预置专家（产品经理、软件工程师、数据分析师、PPT 专家等），支持自定义专家
- **深度调研与产物管理**：联网搜索、网页抓取，自动生成 `.md` / `.docx` / `.pptx` 产物
- **模型与技能管理**：支持任意 OpenAI 兼容接口（OpenAI、DeepSeek、本地 Ollama 等），凭证本机加密存储
- **本地优先**：SQLite 持久化，重启不丢数据

## 📥 下载安装

| 平台 | 下载地址 | 说明 |
|------|----------|------|
| **Windows (x64)** | [SMEbuddyClone-0.1.5-setup.exe](https://github.com/qiyaheng/buddy/releases/latest/download/SMEbuddyClone-0.1.5-setup.exe) | NSIS 安装程序，双击安装，可自选安装目录 |
| **macOS (Apple Silicon)** | [SMEbuddyClone-0.1.5-arm64.dmg](https://github.com/qiyaheng/buddy/releases/latest/download/SMEbuddyClone-0.1.5-arm64.dmg) | DMG 安装镜像，拖入「应用程序」即可 |
| **macOS (zip 备用)** | [SMEbuddyClone-0.1.5-arm64.zip](https://github.com/qiyaheng/buddy/releases/latest/download/SMEbuddyClone-0.1.5-arm64.zip) | zip 压缩包，解压后运行 |

也可以到 [Releases 页面](https://github.com/qiyaheng/buddy/releases) 查看所有版本与产物。

### ⚠️ macOS 首次打开说明

当前安装包为 ad-hoc 签名（无 Apple Developer ID 证书），首次打开时：

1. 在「应用程序」中找到 SMEbuddyClone，**右键 → 打开**，在弹窗中点击「打开」
2. 若提示"应用已损坏"，打开终端执行：

```bash
xattr -cr /Applications/SMEbuddyClone.app
```

## 🚀 本地开发

**前置要求**：Node.js 18+、Python 3.10+

```bash
# 安装依赖
npm ci

# 启动开发模式（自动准备 Python 虚拟环境，Vite 热更新 + Electron 窗口 + 本地 FastAPI）
npm run dev
```

常用命令：

| 命令 | 作用 |
|------|------|
| `npm run dev` | 开发模式启动（默认端口 6173，占用时自动顺延） |
| `npm run build` | 构建前端/主进程产物到 `out/` |
| `npm run backend:test` | 运行后端 pytest 测试 |
| `npm run typecheck` | TypeScript 类型检查 |
| `npm run package:win` | 打包 Windows 安装包（NSIS，输出到 `release/`） |
| `npm run package:mac` | 打包 macOS 安装包（DMG，需在 macOS 上执行） |

## 🏗️ 技术架构

```
┌─────────────────────────────────────────┐
│  Electron 主进程（窗口管理/进程守护）      │
├─────────────────────────────────────────┤
│  React 渲染端（Vite + Ant Design）       │  ←→  SSE 流式事件
├─────────────────────────────────────────┤
│  FastAPI sidecar（Agent 引擎/SQLite）    │  ←→  OpenAI 兼容 LLM API
└─────────────────────────────────────────┘
```

- **前端**：React 18 + TypeScript + Vite + Ant Design 5 + Zustand
- **桌面壳**：Electron 33 + electron-vite + electron-builder
- **后端**：Python FastAPI + SQLAlchemy 2.0（PyInstaller 打包为单文件二进制，随应用分发）
- **数据库**：SQLite（本地持久化）

## 📦 CI 自动构建

推送 `v*` 开头的 tag 会触发 GitHub Actions 同时构建 Windows 与 macOS 安装包，并自动发布到 Release：

```bash
git tag v0.2.0
git push origin v0.2.0
```

也可在仓库 [Actions 页面](https://github.com/qiyaheng/buddy/actions) 手动运行 "Build Desktop Installers" 工作流，产物在 Artifacts 中下载。

## 📄 License

Private / 内部项目
