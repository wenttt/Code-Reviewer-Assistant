# 🤖 AI Code Reviewer

智能代码审查助手 - 使用AI大模型为您的GitHub Pull Request进行专业代码审查

[![GitHub](https://img.shields.io/badge/GitHub-CodeReviewAI-blue)](https://github.com/wenttt/CodeReviewAI)

## ✨ 功能特点

| 功能 | 说明 |
|------|------|
| 🚀 **多模型支持** | DeepSeek (推荐)、OpenAI、Ollama本地模型 |
| 🔒 **安全过滤** | 自动检测并脱敏API Key、密码等敏感信息 |
| 📦 **智能分片** | 大PR自动分片处理，不遗漏任何文件 |
| 📖 **上下文增强** | 获取完整文件内容，提供更准确的审查 |
| 🏠 **本地模式** | 支持Ollama，代码完全不出本地 |

## 🚀 快速开始

### 1. 获取必要的Token

```
✅ GitHub Token: https://github.com/settings/tokens (需要repo权限)
✅ DeepSeek Key: https://platform.deepseek.com/api_keys (推荐，便宜好用)
```

### 2. 启动服务

```bash
# 后端
cd backend
pip install -r requirements.txt
python main.py

# 前端 (新终端)
cd frontend
npm install
npm run dev
```

### 3. 开始使用

1. 打开 http://localhost:3000
2. 输入GitHub Token，点击验证
3. 选择仓库 → 选择PR
4. 配置DeepSeek API Key
5. 点击"开始AI代码审查"

## 📋 审查维度

| 维度 | 权重 | 检查内容 |
|------|------|----------|
| 代码质量 | 30% | 可读性、命名规范、代码结构 |
| 潜在Bug | 25% | 逻辑错误、边界条件、异常处理 |
| 安全问题 | 20% | 输入验证、注入攻击、敏感信息 |
| 性能问题 | 15% | 算法效率、资源使用、查询优化 |
| 最佳实践 | 10% | 设计模式、代码复用、测试覆盖 |

## 🔧 模型配置

### DeepSeek (推荐)

```yaml
优点: 价格便宜 (约OpenAI的1/10)，代码能力强，中文友好
模型: deepseek-chat (推荐) / deepseek-coder
价格: ¥1/百万tokens
```

### OpenAI

```yaml
优点: 综合能力最强
模型: gpt-4o (推荐) / gpt-4-turbo / gpt-3.5-turbo
价格: $5-15/百万tokens
```

### Ollama (本地)

```yaml
优点: 完全免费，数据不出本地
模型: codellama / deepseek-coder / llama3
要求: 本地安装Ollama
```

## 📁 项目结构

```
ai-code-reviewer/
├── backend/
│   ├── main.py              # FastAPI主应用
│   ├── github_client.py     # GitHub API客户端
│   ├── ai_reviewer.py       # AI审查引擎 (支持多模型)
│   ├── security.py          # 敏感信息过滤
│   ├── chunker.py           # 大PR分片处理
│   └── context_analyzer.py  # 上下文分析
├── frontend/
│   └── src/App.jsx          # React前端
├── docs/
│   ├── PRD.md               # 产品需求文档
│   └── GUIDE.md             # 详细使用指南
└── README.md
```

## 📖 详细文档

- [使用指南](docs/GUIDE.md) - 详细配置和使用说明
- [产品文档](docs/PRD.md) - 产品设计和技术方案

## 🔒 安全特性

### 敏感信息过滤

自动检测并脱敏：
- API Keys (OpenAI, GitHub, AWS...)
- 密码和密钥
- JWT Token
- 私钥文件
- 数据库连接字符串
- 内网IP地址

### 数据安全

- GitHub Token仅存储在浏览器本地
- 后端不持久化任何敏感信息
- 支持Ollama本地模型，数据完全不出本地

## 🛠️ API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/auth/validate` | POST | 验证GitHub Token |
| `/api/repos` | GET | 获取仓库列表 |
| `/api/repos/{owner}/{repo}/pulls` | GET | 获取PR列表 |
| `/api/repos/{owner}/{repo}/pulls/{n}/analyze` | GET | 分析PR |
| `/api/review` | POST | 执行AI审查 |

## 📊 评分标准

| 分数 | 等级 | 说明 |
|------|------|------|
| 90-100 | 🏆 优秀 | 代码质量高 |
| 80-89 | 👍 良好 | 少量小问题 |
| 70-79 | 🤔 一般 | 需要改进 |
| 60-69 | ⚠️ 较差 | 明显问题 |
| 0-59 | ❌ 需重构 | 重大修改 |

## 🚧 开发计划

- [x] 多模型支持 (DeepSeek/OpenAI/Ollama)
- [x] 敏感信息过滤
- [x] 大PR智能分片
- [x] 上下文增强
- [ ] GitHub Webhook自动触发
- [ ] 审查结果回写PR评论
- [ ] 自定义审查规则
- [ ] 团队协作功能

## 📄 License

MIT License

---

**Made with ❤️ for better code quality**
