# Edu Agent

面向教育场景的智能对话平台后端，支持 chat / agent / plan 三种问答模式，并提供登录鉴权、会话管理、文件上传、知识库检索增强（RAG）和多轮对话历史。

这不是一个“单纯调大模型接口”的 demo，而是一个可以用来学习 AI 应用工程化的完整项目：它把 FastAPI、SQLite、LangChain、Chroma、文件解析、统一响应、异常处理和前后端联调用在了一起。

## 这个项目是做什么的

它解决的是“围绕学习场景，如何把一个大模型变成能持续对话、能查资料、能做计划、能调用工具的应用”这个问题。

你可以把它理解成一个小型的教育助手平台：
- chat：普通知识问答
- agent：会自主选择工具完成复杂任务
- plan：生成结构化学习计划
- knowledge base：把用户上传的资料做成可检索知识库

## 技术栈

- 后端框架：FastAPI
- 数据库：SQLite
- 大模型编排：LangChain、LangGraph
- 向量库：Chroma / chromadb
- 模型接入：DashScope / Tongyi
- 文件解析：pypdf、docx2txt、Python 标准库解析器
- 配置管理：YAML + 环境变量
- 运行服务：Uvicorn
- 前端联调：Vue3 + Vite + TypeScript + Pinia + axios（独立前端项目）

## 项目架构怎么搭的

项目按“入口层 -> 业务层 -> 仓储层 -> 基础设施层”拆分：

```text
API 路由层
  ├── 负责接收请求、参数校验、返回统一响应
  └── 调用业务服务

业务服务层
  ├── chat / agent / plan 三种模式的核心逻辑
  ├── 负责模型推理、工具编排、RAG 召回
  └── 控制多轮对话与上下文拼接

仓储与基础设施层
  ├── SQLite：用户、token、会话、消息、附件
  ├── Chroma：知识库向量存储
  ├── 文件解析：TXT / PDF / DOCX
  └── 模型工厂：延迟初始化与状态可观测
```

### 为什么这样拆

- 路由层尽量薄，避免把 SQL、模型调用、文件处理都堆在一起
- 对话历史统一放 SQLite，避免 JSON 文件和数据库双写
- 模型工厂采用懒加载，减少启动时直接崩溃的风险
- chat / agent / plan 保持相似的调用入口，方便扩展和测试

## 对初学者有什么用

这个项目很适合拿来学习下面这些基础能力：

- FastAPI 如何组织项目结构、写路由、处理异常、做中间件
- SQLite 如何设计表结构、管理会话和消息历史
- LangChain 工具调用是怎么工作的
- RAG 的基本流程：切分 -> 向量化 -> 检索 -> 生成
- 一个 AI 项目怎么从“能跑”变成“可维护”
- 什么叫统一响应、统一错误码、request_id 排查

如果你是初学者，建议你按这个顺序学：

1. 先看 API 路由怎么进来、怎么返回
2. 再看 SQLite 表结构和消息存储
3. 然后看 chat / agent / plan 的调用差异
4. 最后看 RAG 和工具调用

## 已知不足

这个项目目前也有明显局限，README 里需要明确写出来，避免给人“完美项目”的错觉：

- 模型密钥当前仍放在配置文件里，最好改成环境变量
- 数据库使用 SQLite，适合单机和中小规模场景，但并发能力有限
- 文件上传与知识库入库逻辑还可以进一步解耦
- 目前更偏“项目实践和工程整合”，不是生产级高并发系统
- 自动化测试和 CI 还可以继续补强

## 项目结构

- `api/`：FastAPI 路由、启动入口、统一异常处理
- `agent/`：agent 模式与工具编排
- `chat/`：chat 模式问答逻辑
- `plan/`：plan 模式学习规划逻辑
- `rag/`：检索增强服务与向量库逻辑
- `model/`：模型工厂、懒加载、初始化状态
- `utils/`：配置、日志、文件处理、对话仓储
- `config/`：YAML 配置
- `prompts/`：提示词模板

## 快速启动

### 1. 安装依赖

建议使用 Python 3.10 或 3.11，并在虚拟环境中运行：

```bash
pip install -r requirements.txt
```

### 2. 配置模型密钥

当前代码从 `config/rag.yaml` 读取模型相关配置。

建议做法：

- 将 API key 改为环境变量
- 本地开发时再通过 `.env` 或终端导出

### 3. 启动后端

推荐在项目根目录执行：

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

或者兼容你的运行方式：

```bash
cd api
python main.py
```

### 4. 验证是否启动成功

- API: http://127.0.0.1:8000
- 文档: http://127.0.0.1:8000/docs
- 健康检查: http://127.0.0.1:8000/health

## 从零构造这个项目

如果你想自己重新搭一个类似项目，可以按下面的步骤做：

### 阶段 1：先搭骨架

1. 建一个 FastAPI 项目
2. 先写 `/health`、`/status`、`/auth/login` 这种最小接口
3. 把统一响应和统一异常处理先做出来

### 阶段 2：再上数据层

1. 设计用户表、token 表、会话表、消息表、附件表
2. 先让会话历史能存、能查、能删
3. 把消息流和文件上传分开处理

### 阶段 3：接入 AI 能力

1. 先做一个最简单的 chat 问答
2. 再做 RAG：文件解析、切分、向量化、召回
3. 再做 agent：工具定义、工具中间件、模型调度
4. 最后做 plan：从问答变成结构化计划

### 阶段 4：做工程化收敛

1. 把模型初始化改成懒加载
2. 加 request_id 和日志
3. 统一错误码和返回结构
4. 补 README、requirements、.gitignore

## 主要接口

- POST `/auth/register`
- POST `/auth/login`
- GET `/auth/me`
- GET `/chat/sessions`
- POST `/chat/sessions`
- DELETE `/chat/sessions/{session_id}`
- GET `/chat/sessions/{session_id}/messages`
- POST `/chat/sessions/{session_id}/ask`
- POST `/chat/sessions/{session_id}/upload`
- POST `/knowledgebase/kb/upload`

## 统一响应格式

项目统一使用下面的返回结构：

```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "request_id": "uuid"
}
```

错误示例：

```json
{
  "code": 404,
  "message": "Session not found",
  "data": null,
  "request_id": "uuid"
}
```

## 常见问题

### 1. No module named fastapi

说明当前 Python 环境没有装依赖：

```bash
pip install -r requirements.txt
```

### 2. PDF / DOCX 解析失败

确认安装了：

- pypdf
- docx2txt

### 3. 登录后页面不跳转

通常是前后端返回结构不一致导致的。前端要按 `data` 解包，而不是直接读旧字段。

## 开发建议

- 新接口优先保持统一响应结构
- 不要把工具调用结果直接混进对话历史主表
- 密钥不要明文放进仓库，优先环境变量
- 后续如果要扩展生产能力，可以考虑把 SQLite 迁移为 MySQL / PostgreSQL
