# SMEbuddy 风格 AI 桌面工作台 - 实施计划

> 说明：任务按依赖排序；每个任务为一个可独立验证的垂直切片。技术栈 Electron + React18/TS/Vite/AntD5/Zustand（渲染端）、FastAPI/SQLAlchemy2/Pydantic2/SQLite（sidecar 后端），后端经 PyInstaller 打包由 electron-builder 分发。

## Task 1: 单体仓库脚手架与一键开发链路
- **Status**: `completed`
- **Priority**: high
- **Depends On**: None
- **Completion Evidence**:
  - `npm run dev` 一键启动：electron-vite 构建主进程/preload、Vite 在 5173、sidecar uvicorn 在 18790 就绪，Electron 窗口显示「本地引擎已连接 v0.1.0」（截屏 `.data/shot-task1.png`）。
  - `GET /healthz` 返回 `{"status":"ok","version":"0.1.0"}`（TestClient 与 HTTP 双重验证）。
  - `npm run typecheck` 退出码 0；停止 dev 后 18790 端口释放、无残留 uvicorn python 进程；额外增加父进程看门狗防孤儿 sidecar。
- **Description**:
  - 建立 monorepo 目录：`src/`（React 渲染端）、`electron/`（主进程/preload/sidecar 管理）、`backend/`（FastAPI）、`resources/`。
  - 初始化 package.json（Vite + React + TS）、Electron 主进程创建 1280×800 最小窗口、开发模式加载 Vite URL、生产模式加载本地文件。
  - 主进程实现 sidecar 生命周期：dev 下 spawn `python -m uvicorn app.main:app`（使用项目 venv），prod 下 spawn 打包后的 `backend.exe`；轮询 `/healthz` 就绪后显示窗口；窗口关闭/应用退出时 kill 子进程树。
  - FastAPI 最小骨架：`GET /healthz` 返回 200、CORS（仅本地端口）、统一日志配置、应用数据目录解析（`app.getPath('userData')` 下，dev 时用项目 `.data/`）。
  - `npm run dev` 一条命令并行启动 Vite + sidecar + Electron；preload 暴露最小 IPC（openExternal）。
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `rule` TR-1.1: 在已装 Node18+/Python3.11+ 的机器上执行 `npm run dev`，10 秒内 Electron 窗口出现且 `GET /healthz` 返回 200；退出应用后 OS 进程列表中无残留 Python sidecar 进程。证据：启动日志、`/healthz` 响应、进程检查输出。
- **Notes**: requirements.txt 锁定版本；Python venv 创建步骤写入脚本（`backend/` 下提供 dev 脚本或 package.json scripts 自动检测 venv）。

## Task 2: 数据模型与 SQLite 持久化层
- **Status**: `completed`
- **Priority**: high
- **Depends On**: Task 1
- **Completion Evidence**:
  - 10 张表（folders/tasks/messages/artifacts/usage_records/experts/skills/providers/model_configs/app_settings）建表成功；SQLite WAL + foreign_keys 生效。
  - 种子幂等：12 专家 + 3 技能，重复执行不翻倍；Fernet 加密 roundtrip 正确、掩码 `sk-t****cdef`；删任务级联删消息；跨 Session 数据可读（自检全部断言通过）。
- **Description**:
  - SQLAlchemy 2.0 模型：Folder、Task、Message（含有序过程块 JSON：think/plan/tool/artifact）、Expert、Skill、Provider（含加密 api_key）、ModelConfig、Artifact、UsageRecord、AppSettings（KV）。
  - SQLite WAL 模式、引擎/session 管理、首次启动 `create_all` + 种子数据装配钩子。
  - repository/service 分层封装 CRUD；Pydantic v2 schemas 集中在 `backend/app/schemas/`，作为接口契约单一事实源。
- **Acceptance Criteria Addressed**: AC-5
- **Test Requirements**:
  - `rule` TR-2.1: 向各表写入并重启后端进程后数据仍可读出；外键删除策略（删任务级联删消息/产物记录）生效。证据：pytest 临时库用例通过。
  - `rule` TR-2.2: Provider 的 api_key 落盘为密文，代码与数据库文件中均不出现明文（界面掩码由 Task 3 验证）。证据：用例断言密文 != 明文且可解密还原。

## Task 3: 模型/搜索设置接口与连接测试
- **Status**: `completed`
- **Priority**: high
- **Depends On**: Task 2
- **Completion Evidence**:
  - respx mock 验证连接测试分类：success / auth_failed(401) / timeout(ReadTimeout) / network(ConnectError) 全部正确返回；Provider 列表不含明文 key（掩码 + has_api_key）。
  - 统一错误结构：404→`not_found`、参数错误→`validation_error`(422)、未捕获异常→`internal_error`(500) 且堆栈仅落日志；搜索源设置加密存储、接口掩码。
  - 自检修复真实 bug：AppSetting 误用主键查询导致重复插入唯一约束冲突，已改为按 key 查询。
- **Description**:
  - REST API：Provider CRUD（base_url、api_key 加密、超时）、其下 ModelConfig CRUD（model_id、显示名、能力标签）、搜索源设置（DuckDuckGo 默认 / Tavily key 可选）、连接测试端点（发起 1 token 的最小 chat 请求并回传成功/错误分类）。
  - 错误分类：401/403 → 凭证错误；连接超时/DNS → 网络错误；其余回传状态码与消息。
  - 通用错误响应体与日志中间件（异常落日志文件）。
- **Acceptance Criteria Addressed**: AC-2, AC-12
- **Test Requirements**:
  - `rule` TR-3.1: 用 respx/httpx mock 验证连接测试对 200/401/超时分别返回 success/auth_failed/network；GET 接口返回的 api_key 为掩码。证据：pytest 用例。
  - `rule` TR-3.2: 错误响应结构统一（code/message/details），异常被记录到日志文件且不向客户端泄漏堆栈明文（message 可读即可）。证据：用例 + 日志文件断言。

## Task 4: 渲染端应用外壳、三栏框架与配置引导
- **Status**: `completed`
- **Priority**: high
- **Depends On**: Task 3
- **Completion Evidence**:
  - TR-4.1（配置引导闭环，浏览器自动化全链路走查通过）：全新数据下首页显示「配置你的第一个模型」引导（`.data/step1-homepage.png`）；在设置页创建 Provider（`https://api.example.com/v1` + Key）+ 默认模型 GPT-4o Mini 后，密钥掩码显示 `sk-t****cdef`、模型行带默认星标（`.data/task4-settings-providers.jpg`）；测试连接对不可达端点正确返回红色失败 Alert（`.data/step5-connection-test-result.png`）；返回任务台引导消失并显示欢迎页（`.data/task4-chat-welcome.jpg`）；配置经 SQLite 持久化（走查后经 API 清理，setup 恢复 `has_models=false`）。
  - 搜索源切换 Tavily 并保存加密 Key 成功；连接器 6 卡片「即将推出」（`.data/task4-connectors.jpg`）；关于页显示版本/平台/数据目录（`.data/task4-about.jpg`）；编辑服务商表单正确回填、Key 留空提示「已保存掩码，不修改」。
  - 三栏拖拽：派发鼠标事件将侧栏 248→310px，`localStorage.wb-prefs` 写入且刷新后恢复；右栏可折叠并持久化；折叠后在主区右上新增「展开产物面板」按钮（修复了折叠后无法展开的缺陷）。
  - `npm run typecheck` 退出码 0；dev 停止后端口释放、无残留 python。
  - 交付物：AntD5 主题（品牌渐变 #4f7cff→#7b5cff、zhCN）、HashRouter（/chat/:taskId?、/experts、/settings）、Resizer、Sidebar、ResultPanel、http/SSE 客户端、app/config 两个 store（tasks/chat store 延后到 Task 6/7 按需创建）、设置模块按 AC-U4 拆分为 ProvidersTab/ProviderFormModal/ModelFormModal/SearchTab/ConnectorsTab/AboutTab；纯浏览器联调回退（18790-18810 端口探测），生产仍走 preload。
  - 遗留至 Task 17：PPT 场景图标（SlidersOutlined 观感不贴切）、连接器 emoji 品牌贴合度。
- **Description**:
  - AntD5 主题与全局样式（CSS 变量：品牌色、间距、圆角、专家头像色板）；React Router 路由：`/chat/:taskId?`、`/experts`、`/settings`。
  - 工作台三栏布局：左侧栏（导航图标 + 任务区，Task 8 填充）、中间对话区占位、右侧结果区可折叠；栏宽可拖拽并持久化；窗口标题栏区预留。
  - API 客户端（fetch 封装 + SSE EventSource/流式 fetch 工具）、Zustand stores（config、tasks、chat）。
  - 设置页：Provider/模型增删改、API Key 掩码录入、测试连接按钮（结果提示）、搜索源设置、连接器「即将推出」展示区。
  - 全局「无可用模型」引导卡片与未配置拦截（发送前检查，跳转设置）。
- **Acceptance Criteria Addressed**: AC-2
- **Test Requirements**:
  - `rule` TR-4.1: 全新数据下首页显示配置引导且无法发起任务；配置一个 Provider+模型并测试连接成功后，引导消失、设置持久化，重启应用配置仍在。证据：操作截图与重启验证。
  - `rubric` TR-4.2: 外壳布局质量；scale 1-5；anchors 1=三栏错乱不可用，3=结构正确但样式粗糙，5=间距/配色/折叠/拖拽细节精致；threshold >= 4；evidence 主界面截图。

## Task 5: 任务、文件夹与消息 REST API
- **Status**: `completed`
- **Priority**: high
- **Depends On**: Task 2
- **Completion Evidence**:
  - 新增 `schemas/workspace.py`、`services/workspace_service.py`、`api/folders.py`、`api/tasks.py` 并注册路由；pytest 基础设施 `backend/tests/conftest.py`（临时数据目录 + 全新 SQLite + 种子）。
  - `python -m pytest tests -q` → **10 passed**：文件夹 CRUD/重名 409/空白 400、删文件夹任务回落未分组（SET NULL）、任务创建（专家/技能/模型快照，无模型时快照为空仍可建）、非法引用 404、移动/重命名/状态流转与非法状态 422、标题+消息内容 ilike 搜索、`folder_id=none` 未分组过滤、消息顺序与 blocks、用量汇总（2 条记录累加 120/60/180）、删任务级联清除 Message/Artifact/UsageRecord 且删除磁盘 `artifacts/<task_id>/`、目录配置删除后任务快照完整保留。
- **Description**:
  - Folder CRUD；Task CRUD（标题、所属文件夹、专家/技能/模型快照、状态：idle/running/stopped/error）、任务列表搜索（标题与消息内容 LIKE）、移动、删除（二次确认由前端保证；后端级联产物记录，文件删除由 Task 12 的服务复用）。
  - Message 列表按任务返回（含过程块顺序）；任务级用量汇总接口。
- **Acceptance Criteria Addressed**: AC-5
- **Test Requirements**:
  - `rule` TR-5.1: 任务/文件夹 CRUD、搜索、移动、级联删除的 pytest 用例全部通过；删除任务后消息与产物记录不可查但事务一致。证据：测试输出。

## Task 6: Agent 引擎——LLM 客户端、SSE 事件协议与可中断 Loop
- **Status**: `completed`
- **Priority**: high
- **Depends On**: Task 3
- **Description**:
  - OpenAI 兼容 chat.completions 客户端（base_url/key/超时/模型切换），消费 stream chunk 与 usage。
  - 事件协议（SSE `text/event-stream`）：`plan`、`think`、`tool_call`（started/finished/error 状态负载：名称、输入摘要、来源、耗时）、`message_delta`、`artifact`（id/name/format/size）、`usage`、`done`、`error`。
  - Agent Loop：system 组装（专家 prompt + 启用技能 prompt + 工具说明）→ 多轮工具调用（函数 schema 注入）→ 工具执行结果回灌 → 最大轮次与单任务超时；任务级取消（asyncio.CancelledError 经客户端断链/停止端点触发），取消后不发起新模型请求。
  - 消息与过程块、usage 在每事件后增量落库（重启可见过程）。
  - LLM 抽象接口便于 mock；401/网络/超时分类转 `error` 事件。
- **Acceptance Criteria Addressed**: AC-3, AC-4, AC-12
- **Test Requirements**:
  - `rule` TR-6.1: 用脚本化 fake LLM（顺序返回 tool_call → final）在 pytest 中验证事件序列包含 plan/tool_call/message_delta/artifact/done 且按序；取消信号触发后断言无新 LLM 请求。证据：pytest 输出与事件序列断言。
  - `rule` TR-6.2: fake LLM 抛出 401/超时/连接错误时各产出对应 `error` 事件且任务状态为 error，已落库内容保留。证据：pytest 用例。
  - `rule` TR-6.3: 执行中断掉后端进程再重启，前端重新进入任务能读到已持久化的过程块与消息。证据：集成脚本验证。
- **Completion Evidence**（2026-09-24）:
  - 新增：[events.py](file:///d:/AIproject/jobTwo/backend/app/agent/events.py)（SSE 协议常量+`sse_dumps`）、[state.py](file:///d:/AIproject/jobTwo/backend/app/agent/state.py)（`RunControl` 取消信号+`llm_requests` 计数、`RunRegistry` 运行态互斥）、[prompts.py](file:///d:/AIproject/jobTwo/backend/app/agent/prompts.py)（专家+技能+基座 system 组装、历史消息拼装）、[fake.py](file:///d:/AIproject/jobTwo/backend/app/agent/fake.py)（脚本化 Agent：plan/think/tool/message/artifact/usage 全事件；`SMEBUDDY_FAKE_LLM/STEP/ERROR` 环境变量驱动）、[runner.py](file:///d:/AIproject/jobTwo/backend/app/agent/runner.py)（预校验+双消息落库、事件→blocks 增量归并、每事件 to_thread 落盘、done/stopped/error 收口、断链 CancelledError shield 落盘、产物写文件入库、UsageRecord）、[schemas/chat.py](file:///d:/AIproject/jobTwo/backend/app/schemas/chat.py)、[api/runs.py](file:///d:/AIproject/jobTwo/backend/app/api/runs.py)（`POST /api/tasks/{id}/runs` SSE、`POST /stop`）；扩展 [llm.py](file:///d:/AIproject/jobTwo/backend/app/agent/llm.py)：AsyncOpenAI 流式 `stream_chat`（stream_options include_usage 400 自动降级、reasoning_content→think、chunk 边界检查取消）+ `classify_upstream_error`（auth_failed/rate_limited/timeout/network/bad_request/upstream_error）。
  - 事件类型最终集：run_started / plan_start / plan_update / think_start / think_delta / tool_call / tool_result / message_delta / artifact / usage / stopped(含 llm_requests) / error / done；blocks 落库形态：plan（steps 状态机 pending→running→done）、think（累计 text）、tool（status/input_summary/summary/sources/elapsed_ms）、artifact（id/filename/format/kind/size_bytes）。
  - 真实多轮工具循环（函数 schema 注入、结果回灌、最大轮次）随 Task 11 调研技能接入；Task 6 真实模型路径为 system+历史流式对话。
  - 测试：新增 [test_agent_runner.py](file:///d:/AIproject/jobTwo/backend/tests/test_agent_runner.py) 11 用例（完整序列+顺序+计划推进+工具负载+usage 530+产物文件+消息/任务落库+用量汇总；停止后无 done/artifact 且 llm_requests 不增+状态 stopped+过程块保留+可重跑；并发 409；auth_failed/timeout/network 参数化错误事件+任务 error+思考内容保留；新 Session 直读 SQLite 验证重启可见性；无模型 400、未知任务 404、空白内容、idle stop 幂等）。修复 [workspace_service.py](file:///d:/AIproject/jobTwo/backend/app/services/workspace_service.py) 消息排序（同微秒 user/assistant 按 role_order）与 [conftest.py](file:///d:/AIproject/jobTwo/backend/tests/conftest.py) 数据目录隔离（顶层 setenv 先于测试模块收集期 import，杜绝串开发库）。
  - 验证命令：`pytest tests -q` → **21 passed**；`npm run typecheck` → 0 错误。
  - 真实 uvicorn（非 TestClient）E2E：1s 内增量收到 8 事件（证明非缓冲）；`POST /stop` 后流在 think 阶段终止、无 artifact/done、task/assistant=stopped；curl 断链自动收口 stopped；完整流 26 事件以 done 结束、fake-report.md(453B) 落盘、usage 320/210/530 落库。E2E 临时脚本已删除，开发库已清理恢复仅种子数据，端口 18790 已释放。


## Task 7: 对话区 UI——流式消息流、输入框与中断
- **Status**: `completed`
- **Priority**: high
- **Depends On**: Task 6, Task 4
- **Description**:
  - 消息流组件：用户气泡、Agent 正文（Markdown 渲染：表格/代码高亮/链接）、规划步骤清单（状态勾选）、思考折叠块、工具调用卡片（搜索词、结果条数、来源标题+可点 URL、耗时、状态图标，可折叠）、产物卡片（Task 13 联动）。
  - 流式 store：消费 SSE 增量更新当前消息；自动滚动（用户上滚时不强制打断）；运行态骨架与光标动效。
  - 输入框：多行自增高、Enter 发送/Shift+Enter 换行、附件按钮占位（禁用态提示）、技能/模型选择入口（Task 14 接线，先放控件占位）、运行中切换为「停止生成」，停止调用取消接口/断开流。
  - 任务标题栏：标题重命名、状态徽标、token 用量入口。
  - 错误条内联展示（可读原因 + 重试），不白屏、不丢失已输入文本。
- **Acceptance Criteria Addressed**: AC-3, AC-4, AC-12
- **Test Requirements**:
  - `rule` TR-7.1: 联调（可 mock LLM）确认各事件类型各有对应 UI 元素且在 done 前已逐块出现；停止后 1 秒内输入框恢复并可继续发送。证据：录屏/连续截图与浏览器 DOM 断言。
  - `rubric` TR-7.2: 过程呈现质感；scale 1-5；anchors 1=纯文本流，3=分块但无折叠/状态，5=分组清晰、折叠顺滑、状态与动效细腻；threshold >= 4；evidence 执行过程截图。
- **Completion Evidence**（2026-09-25）:
  - 新增渲染端：类型 [chat.ts](file:///d:/AIproject/jobTwo/src/renderer/src/types/chat.ts)（plan/think/tool/artifact 块与 UIMessage/RunEvent/UsageTally）、[chat-store.ts](file:///d:/AIproject/jobTwo/src/renderer/src/stores/chat-store.ts)（SSE 增量消费、与后端同构的 `mergeEvent` blocks 归并、sessionSeq 防跨任务串事件、建任务→navigate→streamPost、停止/重试/重命名、流内错误挂消息、流外错误 notice+草稿回填）；组件 [Markdown.tsx](file:///d:/AIproject/jobTwo/src/renderer/src/components/chat/Markdown.tsx)（react-markdown+gfm+rehype-highlight，链接走 wb.openExternal）、[PlanBlock.tsx](file:///d:/AIproject/jobTwo/src/renderer/src/components/chat/blocks/PlanBlock.tsx)、[ThinkBlock.tsx](file:///d:/AIproject/jobTwo/src/renderer/src/components/chat/blocks/ThinkBlock.tsx)（流式自动展开、结束自动收起、手点切换）、[ToolBlock.tsx](file:///d:/AIproject/jobTwo/src/renderer/src/components/chat/blocks/ToolBlock.tsx)（联网搜索/读取网页、执行态/耗时绿勾/错误、折叠详情+来源外链）、[ArtifactBlock.tsx](file:///d:/AIproject/jobTwo/src/renderer/src/components/chat/blocks/ArtifactBlock.tsx)（彩色图标+文件名+体积）、[AgentMessage.tsx](file:///d:/AIproject/jobTwo/src/renderer/src/components/chat/AgentMessage.tsx)（专家头像、流式光标、三点骨架、stopped 标签、Alert+重试）、[MessageList.tsx](file:///d:/AIproject/jobTwo/src/renderer/src/components/chat/MessageList.tsx)（距底 80px 吸附滚动+「回到底部」悬浮按钮+用户气泡）、[ChatHeader.tsx](file:///d:/AIproject/jobTwo/src/renderer/src/components/chat/ChatHeader.tsx)（点击重命名/Enter/Esc、running/done/stopped/error 彩色状态徽标、token 用量）、[ChatComposer.tsx](file:///d:/AIproject/jobTwo/src/renderer/src/components/chat/ChatComposer.tsx)（自增高、Enter/Shift+Enter+IME 组合、附件与模型占位 Tooltip、运行中红色「停止生成」）、[ChatWelcome.tsx](file:///d:/AIproject/jobTwo/src/renderer/src/components/chat/ChatWelcome.tsx)（四场景卡带预设 prompt）；重写 [ChatPage.tsx](file:///d:/AIproject/jobTwo/src/renderer/src/pages/ChatPage.tsx)（未配置模型→SetupGuide；空态欢迎页；任务加载、notice 内联 Alert、组装标题栏/列表/输入区）；[global.css](file:///d:/AIproject/jobTwo/src/renderer/src/styles/global.css) 追加约 920 行对话区样式；[App.tsx](file:///d:/AIproject/jobTwo/src/renderer/src/App.tsx) 加 v7_startTransition future flag 消除 Router 警告；[app-store.ts](file:///d:/AIproject/jobTwo/src/renderer/src/stores/app-store.ts) 补存 defaultModelName。
  - 联调修复两个真实竞态：① 新建任务 navigate 触发 `loadTask` 重置 running/递增 sessionSeq，导致进行中流事件全被丢弃、消息卡死在中间快照——loadTask 增加同任务守卫（send 已接管的 taskId 直接 return）；② stop 端点只发信号不等落库，前端断链后 GET 到过时 running 使标题栏永卡「处理中」——stop() 乐观置 stopped，catch 刷新拿到 running 时 800ms 重试一次。
  - 浏览器 E2E（真实 uvicorn sidecar + SMEBUDDY_FAKE_LLM/STEP=0.25，Vite 5173，连续截图 task7-01~11 + DOM 断言）：欢迎页四卡→发送后 1s 计划块逐块出现（running/pending 状态机）且停止按钮已渲染；中段 plan 三步全 done、思考块（70 字）、联网搜索卡运行→完成（420ms、展开 2 条来源标题+URL+摘要）；完成态 Markdown 渲染 h1/h2+6 列表项、流式光标消失、产物卡 fake-report.md（MD · 498 B）、标题栏「已完成」、用量 530 tokens、输入框即时恢复；点停后 1s 内输入框恢复、assistant 挂「已停止生成」标签、停止后可继续发送第 6 轮并正常完成；刷新页面历史回放 5 轮 user/assistant、4 产物/4 工具块、stopped 标签、2120 tokens 累计；标题行内重命名 PATCH 生效；FAKE_ERROR=auth_failed 下错误于 LLM 边界内联为消息级 Alert「[auth_failed] API Key 无效或权限不足（401/403）」+重试按钮，出错前 plan/think 保留，标题栏「出错」，无白屏；长对话出现「回到底部」按钮；控制台无真实错误（仅 Router future 警告，已消除）。
  - 验证命令：`npm run typecheck`（node+web）→ 0 错误；后端回归 `pytest tests -q` → **21 passed**。联调脏数据（6 任务/消息/usage/产物文件）已清空，.data 恢复仅种子（保留一个 Fake Dev Provider 供后续联调），端口已释放。

## Task 8: 侧边栏——任务/文件夹导航与搜索
- **Status**: `completed`
- **Priority**: high
- **Depends On**: Task 5, Task 7
- **Description**:
  - 左侧栏：「新建任务」按钮、文件夹分组（全部任务/未分组/各一级文件夹）、任务条目（标题、时间、运行/错误状态点）、悬停操作（重命名、移动到文件夹、删除）、顶部搜索框（实时过滤）。
  - 底部用户区：设置入口、数据目录/版本号信息。
  - 删除任务二次确认弹窗（告知文件将一并删除，选项文案按 spec Open Question 默认方案）。
- **Acceptance Criteria Addressed**: AC-5
- **Test Requirements**:
  - `rule` TR-8.1: 创建/重命名/移动/删除/搜索任务在 UI 操作后刷新列表与库数据一致；重启后结构保持。证据：操作录屏 + 数据库查询。
  - `rule` TR-8.2: 运行中任务在侧边栏显示运行态指示。证据：截图。
- **Completion Evidence**:
  - 新增 [tasks-store.ts](file:///d:/AIproject/jobTwo/src/renderer/src/stores/tasks-store.ts)（tasks/folders/filter/query；refresh 并行拉取，query 非空走 `/api/tasks?q=`；setFilter/setQuery 280ms 防抖非空自动切 search；renameTask/moveTask 显式 `folder_id:null` 移未分组；removeTask/createFolder/renameFolder/removeFolder，删文件夹后 filter 回 ungrouped 且本地任务 folder_id 置 null 与后端 SET NULL 对齐）；重写 [Sidebar.tsx](file:///d:/AIproject/jobTwo/src/renderer/src/components/Sidebar.tsx)：antd App.useApp 的 modal/message；分组行（全部/未分组/文件夹）计数 badge、InlineEdit 重命名、新建文件夹内联输入；TaskRow 状态点（running 蓝脉冲 wb-pulse/error 红/stopped 橙）、Dropdown（重命名/移动到子菜单带 ✓/删除）、删除任务 modal.confirm「将删除任务「X」及其全部消息与产物文件，删除后不可恢复。」删当前任务 navigate('/chat')；4s 轮询仅在存在 running 任务时发请求；[chat-store.ts](file:///d:/AIproject/jobTwo/src/renderer/src/stores/chat-store.ts) 在 send/run_started/流结束/异常/重命名后 refresh 侧栏（修复运行态点不亮：任务创建为 idle 且轮询条件永不激活）；侧栏重命名后 setState 同步对话页标题（两 store 各持快照）。CSS 采用常驻透明按钮（opacity 0→hover/active/focus-within 显隐，absolute 定位），替代 display:none。
  - 浏览器 E2E（fake 模式，截图 task8-01-running-dot.png / task8-02-delete-confirm.png / task8-03-clean-sidebar.png + DOM 断言）：①TR-8.2 新建任务 run_started 即亮蓝点且仅新任务亮、旧任务完成后蓝点消失，计数实时 +1；②移动任务到「项目 A」后计数 全部2/未分组1/项目A1/项目B0，点项目 A 过滤仅显示该任务；③任务行内重命名 PATCH 即时生效；④搜索"要点一"（消息正文）命中 2 任务、"周报"命中含该消息的任务、无关键词显示「没有匹配的任务」空态；⑤删除任务二次确认弹窗文案/危险按钮正确，确认后列表消失、当前任务跳回 #/chat 欢迎页、计数更新；⑥删除含任务文件夹确认「其中的任务会移动到『未分组』，任务本身不会被删除。」确认后文件夹消失、任务回未分组、筛选自动切未分组；空文件夹删除同路径；⑦新建文件夹+重命名（临时组→临时组改名）；⑧整页 reload 后结构、计数、任务重命名、未分组归属全部保持。
  - 数据库/文件终检（.data/db.sqlite3 + artifacts/）：Q3 任务删除后 messages 无孤儿行（外键级联）、artifacts/cd2051… 产物目录被 best-effort rmtree；删文件夹后 beda8c 任务 folder_id=NULL；联调脏数据已全部清理（tasks/folders/messages 归零，artifacts 清空），保留 Fake Dev Provider 种子。
  - 验证命令：`npm run typecheck`（node+web）→ 0 错误；后端回归保持 **21 passed**。

## Task 9: 专家广场（内置数据 + CRUD + 广场/详情 UI）
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 5, Task 7
- **Description**:
  - 种子 ≥12 专家：产品经理、软件工程师、测试 QA、UI/UX 设计师、运营专家、市场营销、数据分析师、财务顾问、法务顾问、文案写作、行业研究员、PPT 汇报专家；字段：emoji/彩色头像、名称、分类、一句话描述、详情、system_prompt、2~3 推荐问题。
  - Expert CRUD API（内置不可删、可「复制为自定义」；自定义可增改删）。
  - 广场页：分类 Tab/筛选、关键词搜索、专家卡片网格；详情页（能力说明、推荐问题可点直接填入新任务）、「开始任务」创建携带该专家与 system prompt 的任务并跳转对话。
  - 自定义专家编辑表单（名称、emoji 选择、分类、描述、system prompt 编辑器）。
- **Acceptance Criteria Addressed**: AC-6
- **Test Requirements**:
  - `rule` TR-9.1: 种子专家 ≥12 且分类筛选/搜索结果正确；从专家发起任务的首个后端请求 messages 含其 system_prompt（日志/测试断言）；自定义专家增改删闭环可用。证据：pytest + 界面截图 + 后端日志。
  - `rubric` TR-9.2: 卡片视觉质感（彩色头像、排版、hover）；scale 1-5；anchors 1=列表粗糙，3=卡片完整但平庸，5=视觉接近 SMEbuddy 专家团风格；threshold >= 4；evidence 广场页截图。

## Task 10: 联网工具——搜索与网页正文抓取
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 6
- **Description**:
  - 工具 `web_search(query, max_results)`：默认 DuckDuckGo 免 key 实现（结果：标题/URL/摘要），配置 Tavily key 时走 Tavily；统一结果模型与超时/失败降级。
  - 工具 `web_fetch(url)`：httpx 抓取（UA、超时、体积上限），trafilatura/readability 提取正文，返回截断文本与字数。
  - 工具注册进 Agent 工具表（名称、JSON schema、handler、事件摘要渲染器所需元数据）。
- **Acceptance Criteria Addressed**: AC-7
- **Test Requirements**:
  - `rule` TR-10.1: 在线环境下 web_search 对固定查询返回 ≥3 条带 URL 结果；web_fetch 对一个已知静态文章页返回正文长度 > 阈值；无网络/超时返回结构化错误而不抛穿。证据：集成测试（标 `@pytest.mark.network`）+ 离线 mock 用例。

## Task 11: 深度调研技能编排与报告生成
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 10
- **Description**:
  - 内置「深度调研」技能：prompt 编排要求模型先输出搜索子问题计划（plan 事件）、逐题搜索、对高价值结果抓取、去重交叉验证、最后输出结构化 Markdown（摘要/背景/分章发现/结论与建议/参考来源编号列表，正文角标或链接对应 URL）。
  - 通过工具事件暴露搜索词与来源；报告经写文件工具落盘到任务工作目录并登记 artifact（.md）。
  - 技能可被停用（停用后不注入其 system 段与工具约束——搜索工具仍可被其他显式需求调用，注入策略在 Task 14 收口）。
- **Acceptance Criteria Addressed**: AC-7, AC-U3
- **Test Requirements**:
  - `rule` TR-11.1: mock LLM 驱动下调研流程产生 ≥1 次 search 事件、来源 URL 进入最终报告参考列表，且任务目录生成 .md。证据：pytest 事件/文件断言。
  - `rubric` TR-11.2: 用真实兼容模型完成一次指定主题调研的报告质量；scale 1-5；anchors 1=跑题无来源，3=结构尚可但空泛，5=结构完整、紧扣主题、来源真实可点、可直接交付；threshold >= 3；evidence 实际 .md 报告（无可用 key 时记 blocked 并说明）。

## Task 12: 产物生成器（Markdown/Word/PPT）与任务工作目录
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 6
- **Description**:
  - 任务工作目录 `artifacts/<task_id>/`（位于 userData，dev 下 `.data/artifacts`）；写文件工具与产物服务：文件名安全化、去重、元数据登记（格式/大小/时间/任务）。
  - Markdown 直写；`python-docx` 生成 Word（标题层级、段落、列表、表格基本映射）；`python-pptx` 生成 PPT（封面、目录、章节内容页、结尾页的模板化排版，支持从 Markdown 大纲转换）。
  - Agent 可通过 `create_document(name, format, content/outline)` 工具一次任务产出多个文件；删任务时按策略删除目录（默认删除，前端二次确认）。
- **Acceptance Criteria Addressed**: AC-8
- **Test Requirements**:
  - `rule` TR-12.1: 用例分别生成 .md/.docx/.pptx 后，python-docx/python-pptx 能重新打开且 docx 段落数 >0、pptx 页数 ≥2；OOXML 用 zipfile 校验包结构合法；文件登记记录与磁盘一致。证据：pytest 输出与产物路径。
  - `rule` TR-12.2: 删除任务后其工作目录文件被删除（默认路径策略）。证据：用例文件系统断言。

## Task 13: 右侧结果区——产物/文件视图与系统操作 IPC
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 12, Task 7
- **Description**:
  - 结果区两个 Tab：「产物」「全部文件」；列表项：图标/名称/格式/大小/时间，随 artifact 事件实时追加。
  - `.md/.txt` 应用内预览（Markdown 渲染）；通过 Electron IPC 实现：系统默认程序打开文件、在文件管理器中定位、另存为（showSaveDialog + 复制）、外链 openExternal。
  - 对话流中的产物卡片与结果区状态联动（点击卡片定位文件）。
- **Acceptance Criteria Addressed**: AC-9
- **Test Requirements**:
  - `rule` TR-13.1: 四类操作（预览/打开/定位/另存）各成功一次：IPC 日志参数正确，另存目标路径存在且字节一致，外链不被当作本地路径。证据：手工验证录屏 + IPC 单测（preload/main 通道参数校验）。

## Task 14: 技能系统、模型切换与用量统计收口
- **Status**: `pending`
- **Priority**: medium
- **Depends On**: Task 9, Task 11, Task 12
- **Description**:
  - Skill 表与种子（深度调研、文档生成、PPT 生成；描述、启用默认值、prompt 模板）；CRUD API 与启停；自定义技能（名称/触发描述/prompt）。
  - 发起任务时选择挂载技能（输入区 popover，多选），后端组装 system 段；停用技能不注入；任务持久化技能快照。
  - 对话区模型切换器（来自已配置模型），请求体携带所选 model 并落库任务模型快照。
  - 用量统计：累计 usage 事件写 UsageRecord；设置页「用量」区与任务信息展示次数/token。
- **Acceptance Criteria Addressed**: AC-10
- **Test Requirements**:
  - `rule` TR-14.1: 后端测试断言：挂载自定义技能的请求 system 含其模板；停用「深度调研」后普通任务请求不含其 prompt 段且模型不被引导搜索；切换模型后请求体 model 变化。证据：pytest 对组装后请求 payload 的断言。
  - `rule` TR-14.2: usage 事件后用量汇总接口数值递增并可在设置页看到。证据：API 用例 + 截图。

## Task 15: 后端单元测试与工程质量收口
- **Status**: `pending`
- **Priority**: medium
- **Depends On**: Task 14
- **Description**:
  - 用 fake/mock LLM 跑通端到端后端用例：任务创建 → SSE 事件序列 → 工具调用 → 产物登记 → 中断 → 错误分类 → 持久化恢复。
  - 渲染端关键 store/组件测试（Vitest + Testing Library：流式归并、未配置拦截、专家筛选）。
  - TypeScript 严格模式无显式 any 新增（关键链路）；ESLint/Ruff 检查纳入脚本。
- **Acceptance Criteria Addressed**: AC-U4
- **Test Requirements**:
  - `rule` TR-15.1: `pytest` 全绿（网络用例可跳过并显式标注）；`npm run typecheck` 与 lint 零错误；前端测试通过。证据：命令输出。
  - `rubric` TR-15.2: 工程质量走查；scale 1-5；anchors 1=分层混乱无测试，3=基本分层但有 any/缺测试，5=契约集中、分层清晰、mock 测试覆盖关键链路、错误处理统一；threshold >= 4；evidence 目录结构与测试覆盖说明。

## Task 16: PyInstaller + electron-builder Windows 打包
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 15
- **Description**:
  - PyInstaller spec 将后端打成单文件 `backend.exe`（含依赖、种子数据）；构建脚本复制到 `resources/`。
  - electron-builder NSIS x64 配置（artifact 名、图标、extraResources 包含 backend.exe 与运行时；不依赖系统 Python）。
  - 主进程按 prod 路径 spawn sidecar（端口可用段自动选择、健康检查、崩溃提示与重启）。
  - 产出安装包并在干净环境（无 Python）验证安装→启动→配置→发起任务全链路；退出后进程清理。
- **Acceptance Criteria Addressed**: AC-11
- **Test Requirements**:
  - `rule` TR-16.1: 构建产出 `*.exe` 安装包；安装目录含 backend.exe；在无 Python 的 Windows 机器/干净账户下安装启动成功，任务管理器中 sidecar 随应用退出而消失。证据：构建日志、产物文件清单、干净环境截图/进程列表。

## Task 17: 视觉与交互对标打磨
- **Status**: `pending`
- **Priority**: medium
- **Depends On**: Task 13, Task 14
- **Description**:
  - 对照 SMEbuddy 公开界面逐项打磨：空状态/欢迎页（一句话输入 + 推荐任务）、品牌色与渐变、专家头像色板、卡片阴影与 hover、输入框工具栏、产物图标体系、过程动效节奏、深浅用色一致性、中文文案。
  - 响应式最小窗口（1024×684）不错位；滚动条/折叠/徽标细节统一。
- **Acceptance Criteria Addressed**: AC-U1, AC-U2
- **Test Requirements**:
  - `rubric` TR-17.1: SMEbuddy 视觉还原；scale 1-5；anchors 按 spec AC-U1；threshold >= 4；evidence 欢迎页/对话页/广场页/结果区/设置页截图与官网对照。
  - `rubric` TR-17.2: 执行过程可读性与动效；scale 1-5；anchors 按 spec AC-U2；threshold >= 4；evidence 完整任务执行录屏。
