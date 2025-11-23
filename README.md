# AI Story Generator / AI 爆款小说生成器

[English](#english) | [中文](#chinese)

<a name="english"></a>
## 📖 Introduction

The **AI Story Generator** is a comprehensive application designed to assist authors in creating best-selling novels with engaging plots and logical consistency. It leverages a **Multi-Agent** architecture combined with **Monte Carlo Tree Search (MCTS)** for plot optimization, and uses **RAG (Retrieval-Augmented Generation)** with **ChromaDB** to maintain long-term memory of characters, events, and foreshadowing. It also integrates **ScrapingDog** for real-time information retrieval to ensure story authenticity.

## ✨ Features

### 1. Multi-Agent System
-   **Story Planner**: Plans the macro story arc, generating outlines and key plot twists.
-   **Chapter Generator**: Writes detailed chapters, focusing on prose and sensory details.
-   **Critic**: Evaluates generated content based on best-seller criteria and provides feedback.
-   **Researcher**: Searches for real-world data to enrich the story background.

### 2. Core Technologies
-   **MCTS Plot Simulation**: Explores various plot directions to select the most compelling narrative path.
-   **Long-term Memory System**:
    -   **Entity Memory**: Tracks status of characters, items, and locations.
    -   **Event Memory**: Records all key plot points.
    -   **Foreshadowing Management**: Tracks unresolved mysteries and prompts their resolution.
-   **Multi-Model Support**: Compatible with OpenAI API format (GPT-4, Claude, Gemini, DeepSeek, etc.).

### 3. Modern Frontend
-   **Next.js Interface**: Responsive design for an immersive writing experience.
-   **Visual Outline**: Real-time visualization of the story structure.

## 🚀 Deployment Guide

### Prerequisites
-   **LLM API Key** (OpenAI, DeepSeek, etc.)
-   **ScrapingDog API Key** (Optional, for research features)

### Method 1: Docker Deployment (Recommended)

1.  **Install Docker**: Ensure Docker and Docker Compose are installed on your system.
2.  **Configure Environment**:
    Create a `.env` file in the `backend` directory:
    ```env
    LLM_API_KEY=sk-your-key
    LLM_BASE_URL=https://api.openai.com/v1
    LLM_MODEL=gpt-4o
    SCRAPINGDOG_API_KEY=your-key
    ```
3.  **Run**:
    ```bash
    docker-compose up --build -d
    ```
4.  **Access**:
    -   Frontend: `http://localhost:3000`
    -   Backend API: `http://localhost:8000/docs`

### Method 2: Source Code Deployment

1.  **Backend**:
    ```bash
    cd backend
    pip install -r requirements.txt
    # Set env vars: LLM_API_KEY, etc.
    uvicorn app.main:app --reload
    ```
2.  **Frontend**:
    ```bash
    cd frontend/frontend
    npm install
    npm run dev
    ```

---

<a name="chinese"></a>
## 📖 项目简介

**AI 爆款小说生成器** 是一个基于 Multi-Agent 架构的 AI 应用，旨在自动创作情节跌宕起伏、逻辑严密的长短篇小说。系统结合了 **Monte Carlo Tree Search (MCTS)** 算法进行剧情推演，利用 **RAG (Retrieval-Augmented Generation)** 和 **向量数据库 (ChromaDB)** 实现长篇小说的长期记忆和伏笔管理，并集成 **ScrapingDog** 进行实时信息检索。

## ✨ 核心功能

### 1. 多智能体架构 (Multi-Agent System)
-   **Story Planner (剧情策划)**: 负责宏观故事线的规划，生成大纲和关键转折点。
-   **Chapter Generator (章节写作)**: 负责具体章节的描写，注重文笔和画面感。
-   **Critic (评论家)**: 基于畅销书标准对生成的内容进行评分和反馈。
-   **Researcher (研究员)**: 调用外部工具搜索资料，确保故事背景的真实性。

### 2. 核心技术
-   **MCTS 剧情推演**: 使用蒙特卡洛搜索树探索不同的剧情走向，选择最优、最吸引人的情节分支。
-   **长期记忆系统 (Long-term Memory)**:
    -   **实体记忆**: 追踪人物状态、物品归属、地点变化。
    -   **事件记忆**: 记录发生过的所有关键情节。
    -   **伏笔管理**: 自动记录未解之谜，并在后续情节中提示回收。
-   **多模型支持**: 兼容 OpenAI API 格式，支持切换 GPT-4, Claude, Gemini, DeepSeek 等模型。

### 3. 现代化前端
-   **Next.js 界面**: 响应式设计，提供沉浸式的写作和阅读体验。
-   **可视化大纲**: 实时展示故事结构和剧情分支。

## 🚀 部署说明

### 前置准备
-   **LLM API Key**: (如 OpenAI, DeepSeek 等)
-   **ScrapingDog API Key**: (用于联网搜索，可选)

### 方式一：Docker 部署 (推荐)

1.  **安装 Docker**: 确保系统已安装 Docker 和 Docker Compose。
2.  **配置环境变量**:
    在 `backend` 目录下创建 `.env` 文件：
    ```env
    LLM_API_KEY=sk-your-key
    LLM_BASE_URL=https://api.openai.com/v1
    LLM_MODEL=gpt-4o
    SCRAPINGDOG_API_KEY=your-key
    ```
3.  **启动服务**:
    ```bash
    docker-compose up --build -d
    ```
4.  **访问**:
    -   前端: `http://localhost:3000`
    -   后端 API: `http://localhost:8000/docs`

### 方式二：源码部署

1.  **后端**:
    ```bash
    cd backend
    pip install -r requirements.txt
    # 设置环境变量: LLM_API_KEY 等
    uvicorn app.main:app --reload
    ```
2.  **前端**:
    ```bash
    cd frontend/frontend
    npm install
    npm run dev
    ```
