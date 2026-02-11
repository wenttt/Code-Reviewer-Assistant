# AI Code Review - 产品需求文档 (PRD)

## 1. 产品概述

### 1.1 产品名称
**AI Code Reviewer** - 智能代码审查助手

### 1.2 产品愿景
为开发者提供一个智能化的代码审查工具，通过AI大模型自动分析GitHub Pull Request，提供专业、及时、全面的代码审查意见，帮助提升代码质量和开发效率。

### 1.3 目标用户
- 个人开发者
- 小型开发团队
- 开源项目维护者
- 需要快速代码审查反馈的团队

### 1.4 核心价值
- ⚡ **即时反馈**: 创建PR后立即获得AI代码审查
- 🎯 **专业分析**: 基于大模型的深度代码分析
- 🔒 **安全可控**: 使用用户自己的GitHub Token，数据安全有保障
- 💰 **成本节约**: 减少人工审查时间，加速开发流程

---

## 2. 功能需求

### 2.1 核心功能 (MVP)

#### F1: GitHub 认证与授权
| 项目 | 描述 |
|------|------|
| 功能描述 | 用户通过Personal Access Token (PAT) 连接GitHub账户 |
| 输入 | GitHub Personal Access Token |
| 输出 | 认证状态、用户信息、可访问的仓库列表 |
| 验证规则 | Token需要有 `repo` 权限 |

#### F2: 获取PR信息
| 项目 | 描述 |
|------|------|
| 功能描述 | 获取指定仓库的PR列表和PR详细信息 |
| 输入 | 仓库名称 (owner/repo)、PR编号 |
| 输出 | PR标题、描述、变更文件列表、代码diff |
| 数据范围 | 支持获取最近的Open状态PR |

#### F3: AI代码审查
| 项目 | 描述 |
|------|------|
| 功能描述 | 使用AI大模型对PR代码进行审查分析 |
| 输入 | PR的代码变更 (diff) |
| 输出 | 结构化的代码审查报告 |
| 审查维度 | 代码质量、潜在Bug、安全隐患、性能问题、最佳实践建议 |

#### F4: 审查报告展示
| 项目 | 描述 |
|------|------|
| 功能描述 | 以友好的方式展示AI审查结果 |
| 展示内容 | 总体评分、问题列表、改进建议、代码行级注释 |
| 交互方式 | 支持按严重程度筛选、定位到具体代码行 |

### 2.2 扩展功能 (Future)

| 功能 | 描述 | 优先级 |
|------|------|--------|
| GitHub Webhook集成 | PR创建时自动触发审查 | P1 |
| 评论回写 | 将审查结果作为PR评论发布 | P1 |
| 自定义审查规则 | 支持团队自定义代码规范 | P2 |
| 多语言支持 | 支持更多编程语言的专业审查 | P2 |
| 历史记录 | 保存审查历史，支持对比分析 | P3 |
| 团队协作 | 多人共享审查结果 | P3 |

---

## 3. 技术架构

### 3.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户浏览器                                 │
│                    (React Frontend)                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend API Server                          │
│                    (Python FastAPI/Flask)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ Auth Module │  │ GitHub API  │  │   AI Review Engine      │  │
│  │             │  │  Client     │  │   (LLM Integration)     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │                  │                       │
         ▼                  ▼                       ▼
┌─────────────┐    ┌─────────────────┐    ┌─────────────────────┐
│   Cache     │    │   GitHub API    │    │    AI Model API     │
│  (Redis)    │    │   (REST API)    │    │  (OpenAI/Claude)    │
└─────────────┘    └─────────────────┘    └─────────────────────┘
```

### 3.2 技术栈选型

| 层级 | 技术选择 | 理由 |
|------|----------|------|
| **前端** | React + TypeScript + Tailwind CSS | 组件化开发、类型安全、快速样式 |
| **后端** | Python + FastAPI | 异步支持好、开发效率高、AI库丰富 |
| **AI模型** | OpenAI GPT-4 / Claude | 代码理解能力强、支持长上下文 |
| **GitHub API** | PyGithub / 直接REST | 成熟的Python库、完整的API覆盖 |
| **缓存** | 内存缓存 (MVP) | 简化架构，后续可升级Redis |

### 3.3 API设计

#### 3.3.1 认证相关

```
POST /api/auth/validate
Request:  { "token": "ghp_xxxx" }
Response: { "valid": true, "user": { "login": "xxx", "name": "xxx" } }
```

#### 3.3.2 仓库相关

```
GET /api/repos
Response: { "repos": [{ "full_name": "owner/repo", "description": "..." }] }

GET /api/repos/{owner}/{repo}/pulls
Response: { "pulls": [{ "number": 1, "title": "...", "state": "open" }] }
```

#### 3.3.3 PR审查相关

```
GET /api/repos/{owner}/{repo}/pulls/{number}
Response: { "pr": { "title": "...", "files": [...], "diff": "..." } }

POST /api/review
Request:  { "owner": "xxx", "repo": "xxx", "pull_number": 1 }
Response: { 
  "review": {
    "score": 85,
    "summary": "...",
    "issues": [...],
    "suggestions": [...]
  }
}
```

---

## 4. 数据模型

### 4.1 核心数据结构

```typescript
// PR信息
interface PullRequest {
  number: number;
  title: string;
  description: string;
  author: string;
  state: 'open' | 'closed' | 'merged';
  created_at: string;
  files: FileChange[];
  diff: string;
}

// 文件变更
interface FileChange {
  filename: string;
  status: 'added' | 'modified' | 'deleted' | 'renamed';
  additions: number;
  deletions: number;
  patch: string;  // diff内容
}

// 审查结果
interface ReviewResult {
  score: number;           // 0-100 综合评分
  summary: string;         // 总体评价
  issues: ReviewIssue[];   // 发现的问题
  suggestions: string[];   // 改进建议
  reviewed_at: string;     // 审查时间
}

// 审查问题
interface ReviewIssue {
  severity: 'critical' | 'major' | 'minor' | 'info';
  category: 'bug' | 'security' | 'performance' | 'style' | 'maintainability';
  file: string;
  line?: number;
  description: string;
  suggestion?: string;
}
```

---

## 5. 用户流程

### 5.1 主要用户流程

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户流程图                               │
└─────────────────────────────────────────────────────────────────┘

[开始] 
   │
   ▼
[输入GitHub Token] ──────┐
   │                     │ Token无效
   ▼                     ▼
[验证Token] ─────────> [显示错误提示]
   │ 验证成功               │
   ▼                       │
[获取仓库列表]              │
   │                       │
   ▼                       │
[选择仓库]                  │
   │                       │
   ▼                       │
[显示PR列表]                │
   │                       │
   ▼                       │
[选择要审查的PR]            │
   │                       │
   ▼                       │
[获取PR详情和Diff]          │
   │                       │
   ▼                       │
[发送给AI进行审查]          │
   │                       │
   ▼                       │
[显示审查结果]              │
   │                       │
   ▼                       │
[结束] <────────────────────┘
```

### 5.2 页面设计

#### 页面1: 首页/Token配置
- Token输入框
- 验证按钮
- 使用说明

#### 页面2: 仓库选择
- 仓库列表（卡片式）
- 搜索/筛选功能
- 最近访问的仓库

#### 页面3: PR列表
- PR卡片列表
- 状态筛选（Open/Closed/All）
- 快速预览

#### 页面4: 审查结果
- 评分展示（圆环图）
- 问题列表（可折叠）
- 代码预览（高亮问题行）
- 改进建议

---

## 6. 安全考虑

### 6.1 Token安全
- ✅ Token仅存储在客户端（localStorage/sessionStorage）
- ✅ Token通过HTTPS传输
- ✅ 后端不持久化存储Token
- ✅ Token仅用于当前会话

### 6.2 数据安全
- ✅ 代码数据不在服务器持久化存储
- ✅ AI API调用使用加密传输
- ✅ 审查结果可选择性保存

### 6.3 权限最小化
- 建议用户创建只读权限的Token
- 明确告知所需权限范围

---

## 7. MVP开发计划

### 7.1 开发阶段

| 阶段 | 任务 | 预计时间 |
|------|------|----------|
| **Phase 1** | 项目搭建、基础架构 | 0.5天 |
| **Phase 2** | GitHub API集成 | 0.5天 |
| **Phase 3** | AI审查核心逻辑 | 1天 |
| **Phase 4** | 前端界面开发 | 1天 |
| **Phase 5** | 联调测试 | 0.5天 |

### 7.2 MVP功能边界

**包含 (In Scope)**:
- [x] Token验证
- [x] 获取仓库列表
- [x] 获取PR列表
- [x] 获取PR详情和Diff
- [x] AI代码审查
- [x] 结果展示

**不包含 (Out of Scope)**:
- [ ] 用户注册/登录系统
- [ ] 数据持久化
- [ ] Webhook自动触发
- [ ] 评论回写到GitHub
- [ ] 多租户支持

---

## 8. 成功指标

### 8.1 功能指标
- 成功获取PR信息的成功率 > 95%
- AI审查响应时间 < 30秒
- 审查结果准确性用户满意度 > 80%

### 8.2 用户体验指标
- 首次使用到完成审查 < 5分钟
- 页面加载时间 < 3秒
- 操作步骤 < 5步

---

## 9. 附录

### 9.1 GitHub Token权限说明

创建Token步骤:
1. 访问 GitHub Settings > Developer settings > Personal access tokens
2. 点击 "Generate new token (classic)"
3. 勾选以下权限:
   - `repo` - 完整仓库访问（如需私有仓库）
   - `public_repo` - 公开仓库访问（仅公开仓库）

### 9.2 AI模型Prompt设计

```
你是一位资深的代码审查专家。请对以下Pull Request的代码变更进行全面审查。

审查维度:
1. 代码质量 - 可读性、可维护性、代码规范
2. 潜在Bug - 逻辑错误、边界条件、异常处理
3. 安全问题 - 注入攻击、敏感信息泄露、权限问题
4. 性能问题 - 算法效率、资源使用、内存泄漏
5. 最佳实践 - 设计模式、代码复用、测试覆盖

请以JSON格式输出审查结果...
```

### 9.3 参考资源
- [GitHub REST API文档](https://docs.github.com/en/rest)
- [OpenAI API文档](https://platform.openai.com/docs)
- [PyGithub文档](https://pygithub.readthedocs.io/)

---

*文档版本: 1.0*  
*创建日期: 2026-02-11*  
*作者: AI Code Reviewer Team*
