"""
AI Code Reviewer - AI Review Engine (Enhanced)
使用大语言模型进行代码审查的核心模块 - 增强版
支持：敏感信息过滤、大PR分片、上下文增强、本地模型
"""

import json
import os
import httpx
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum
from openai import AsyncOpenAI

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    from google import genai
    from google.genai import types
    HAS_GOOGLE_GENAI = True
except ImportError:
    HAS_GOOGLE_GENAI = False

from github_client import PullRequest, FileChange
from security import SensitiveFilter, SecurityConfig, SensitiveMatch
from chunker import PRChunker, ReviewChunk, FileClassifier, FilePriority, aggregate_chunk_reviews, ChunkReviewResult
from context_analyzer import ContextEnhancer, FileContext, build_context_prompt, LanguageDetector


class IssueSeverity(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


class IssueCategory(str, Enum):
    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    MAINTAINABILITY = "maintainability"
    BEST_PRACTICE = "best_practice"


class ModelProvider(str, Enum):
    OPENAI = "openai"
    DEEPSEEK = "deepseek"      # DeepSeek API
    ANTHROPIC = "anthropic"    # Anthropic Claude API
    GEMINI = "gemini"          # Google Gemini API
    AZURE = "azure"
    OLLAMA = "ollama"          # 本地模型
    CUSTOM = "custom"          # 自定义API (公司自建/第三方兼容OpenAI接口)


@dataclass
class ReviewIssue:
    severity: str
    category: str
    file: str
    line: Optional[int]
    description: str
    suggestion: Optional[str]


@dataclass
class ReviewResult:
    score: int
    summary: str
    issues: List[ReviewIssue]
    highlights: List[str]
    suggestions: List[str]
    # 新增字段
    filtered_secrets: List[Dict] = None  # 被过滤的敏感信息
    chunks_count: int = 1  # 分片数量
    skipped_files: List[str] = None  # 跳过的文件
    context_enhanced: bool = False  # 是否使用了上下文增强
    
    def to_dict(self):
        result = {
            "score": self.score,
            "summary": self.summary,
            "issues": [asdict(issue) for issue in self.issues],
            "highlights": self.highlights,
            "suggestions": self.suggestions,
            "chunks_count": self.chunks_count,
            "context_enhanced": self.context_enhanced,
        }
        if self.filtered_secrets:
            result["filtered_secrets_count"] = len(self.filtered_secrets)
            result["filtered_secrets"] = [
                {"type": s["type"], "file": s["file"], "line": s["line"]} 
                for s in (self.filtered_secrets or [])
            ]
        if self.skipped_files:
            result["skipped_files"] = self.skipped_files
        return result


@dataclass
class ReviewConfig:
    """审查配置"""
    # 安全设置
    enable_security_filter: bool = True
    security_mode: str = "mask"  # mask | warn | block
    
    # 分片设置
    enable_chunking: bool = True
    max_tokens_per_chunk: int = 8000
    max_files_per_chunk: int = 15
    
    # 上下文设置
    enable_context_enhancement: bool = True
    fetch_full_files: bool = True
    
    # 模型设置
    provider: ModelProvider = ModelProvider.OPENAI
    model: str = "gpt-4o"
    temperature: float = 0.3
    
    # Ollama设置 (本地模型)
    ollama_base_url: str = "http://localhost:11434"
    
    # DeepSeek设置
    deepseek_base_url: str = "https://api.deepseek.com"
    
    # Anthropic Claude设置
    anthropic_base_url: str = "https://api.anthropic.com"
    
    # Google Gemini设置
    gemini_base_url: str = ""  # 留空使用默认
    
    # 自定义API设置 (兼容OpenAI接口的公司内部/第三方服务)
    custom_base_url: str = ""
    custom_model_name: str = ""


class AIReviewEngine:
    """AI代码审查引擎 - 增强版"""
    
    SYSTEM_PROMPT = """你是一位资深的代码审查专家，拥有10年以上的软件开发经验。你精通多种编程语言，对代码质量、安全性、性能优化有深入理解。

你的任务是对Pull Request的代码变更进行全面、专业的审查。

## 审查维度

1. **代码质量** (权重30%)
   - 代码可读性和清晰度
   - 命名规范（变量、函数、类）
   - 代码结构和组织
   - 注释的充分性和准确性

2. **潜在Bug** (权重25%)
   - 逻辑错误
   - 边界条件处理
   - 空值/异常处理
   - 类型安全

3. **安全问题** (权重20%)
   - 输入验证
   - SQL注入、XSS等注入攻击
   - 敏感信息泄露
   - 认证和授权问题

4. **性能问题** (权重15%)
   - 算法效率
   - 资源使用（内存、CPU）
   - 数据库查询优化
   - 缓存使用

5. **最佳实践** (权重10%)
   - 设计模式应用
   - 代码复用
   - 测试覆盖
   - 文档完整性

## 上下文分析

当提供了完整文件内容时，请特别注意：
- 修改的函数是否影响了其他调用它的地方
- 新增的代码是否与现有代码风格一致
- 导入的模块是否被正确使用
- 是否存在未使用的导入或变量

## 输出格式

请严格按照以下JSON格式输出审查结果：

```json
{
  "score": 85,
  "summary": "总体评价，100字以内",
  "issues": [
    {
      "severity": "critical|major|minor|info",
      "category": "bug|security|performance|style|maintainability|best_practice",
      "file": "文件路径",
      "line": 行号或null,
      "description": "问题描述",
      "suggestion": "修改建议"
    }
  ],
  "highlights": ["代码亮点1", "代码亮点2"],
  "suggestions": ["改进建议1", "改进建议2"]
}
```

## 评分标准

- 90-100: 优秀，代码质量高，几乎无问题
- 80-89: 良好，有少量小问题
- 70-79: 一般，有一些需要改进的地方
- 60-69: 较差，存在明显问题
- 0-59: 需要重大修改

## 注意事项

1. 审查要客观、专业，给出具体的问题描述和改进建议
2. 区分问题的严重程度，不要把所有问题都标为critical
3. 不仅指出问题，也要肯定代码中的优点
4. 建议要具体可行，最好能给出代码示例
5. 考虑代码的上下文和项目特点
6. 如果代码中有 [REDACTED] 或 *** 标记，说明敏感信息已被过滤，不要对此提出问题"""

    def __init__(
        self, 
        api_key: str, 
        base_url: Optional[str] = None,
        config: Optional[ReviewConfig] = None
    ):
        self.config = config or ReviewConfig()
        self.api_key = api_key
        self.security_filter = SensitiveFilter()
        self.chunker = PRChunker(
            max_tokens=self.config.max_tokens_per_chunk,
            max_files=self.config.max_files_per_chunk
        )
        
        # 初始化AI客户端 (根据provider选择不同的客户端)
        self.client = None           # OpenAI兼容客户端
        self.anthropic_client = None # Anthropic原生客户端
        self.gemini_client = None    # Google Gemini客户端
        
        if self.config.provider == ModelProvider.OLLAMA:
            # Ollama使用OpenAI兼容接口
            self.client = AsyncOpenAI(
                api_key="ollama",
                base_url=f"{self.config.ollama_base_url}/v1"
            )
        elif self.config.provider == ModelProvider.DEEPSEEK:
            # DeepSeek使用OpenAI兼容接口
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url or self.config.deepseek_base_url
            )
        elif self.config.provider == ModelProvider.ANTHROPIC:
            # Anthropic Claude 使用原生SDK
            if not HAS_ANTHROPIC:
                raise ImportError(
                    "请安装 anthropic 包: pip install anthropic"
                )
            client_kwargs = {"api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url
            elif self.config.anthropic_base_url and self.config.anthropic_base_url != "https://api.anthropic.com":
                client_kwargs["base_url"] = self.config.anthropic_base_url
            self.anthropic_client = anthropic.AsyncAnthropic(**client_kwargs)
        elif self.config.provider == ModelProvider.GEMINI:
            # Google Gemini 使用原生SDK
            if not HAS_GOOGLE_GENAI:
                raise ImportError(
                    "请安装 google-genai 包: pip install google-genai"
                )
            self.gemini_client = genai.Client(api_key=api_key)
        elif self.config.provider == ModelProvider.CUSTOM:
            # 自定义API - 兼容OpenAI接口 (公司自建/第三方服务)
            custom_url = base_url or self.config.custom_base_url
            if not custom_url:
                raise ValueError(
                    "自定义API需要提供 Base URL，请填写您的API服务地址，"
                    "例如: https://your-company.com/v1"
                )
            self.client = AsyncOpenAI(
                api_key=api_key or "custom-key",
                base_url=custom_url
            )
        else:
            # OpenAI 官方
            client_kwargs = {"api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url
            self.client = AsyncOpenAI(**client_kwargs)
    
    def _filter_sensitive_content(
        self, 
        files: List[FileChange]
    ) -> tuple[List[FileChange], List[SensitiveMatch]]:
        """过滤文件中的敏感信息"""
        if not self.config.enable_security_filter:
            return files, []
        
        filtered_files = []
        all_matches = []
        
        for file in files:
            if file.patch:
                filtered_patch, matches = self.security_filter.filter_content(
                    file.patch, 
                    file.filename
                )
                # 创建新的FileChange对象，避免修改原对象
                filtered_file = FileChange(
                    filename=file.filename,
                    status=file.status,
                    additions=file.additions,
                    deletions=file.deletions,
                    changes=file.changes,
                    patch=filtered_patch
                )
                filtered_files.append(filtered_file)
                all_matches.extend(matches)
            else:
                filtered_files.append(file)
        
        return filtered_files, all_matches
    
    def _prepare_review_content(
        self, 
        pr: PullRequest, 
        files: List[FileChange],
        context: Optional[List[FileContext]] = None
    ) -> str:
        """准备审查内容"""
        content_parts = []
        
        # PR基本信息
        content_parts.append("## Pull Request 信息")
        content_parts.append(f"- **标题**: {pr.title}")
        content_parts.append(f"- **描述**: {pr.body or '无描述'}")
        content_parts.append(f"- **分支**: {pr.head_ref} → {pr.base_ref}")
        content_parts.append(f"- **变更统计**: +{pr.additions} -{pr.deletions} 行，{pr.changed_files} 个文件")
        content_parts.append("")
        
        # 如果有完整上下文
        if context:
            content_parts.append("## 完整文件内容（用于上下文理解）")
            for ctx in context:
                content_parts.append(f"\n### {ctx.filename}")
                if ctx.functions:
                    func_names = [f.name for f in ctx.functions[:10]]
                    content_parts.append(f"**定义的函数**: {', '.join(func_names)}")
                # 限制内容长度
                file_content = ctx.content
                if len(file_content) > 3000:
                    file_content = file_content[:3000] + "\n... (内容截断)"
                content_parts.append(f"```{ctx.language.value}")
                content_parts.append(file_content)
                content_parts.append("```")
            content_parts.append("")
        
        # 文件变更详情
        content_parts.append("## 变更文件列表")
        for f in files:
            priority = FileClassifier.get_priority(f)
            priority_emoji = {
                FilePriority.CRITICAL: "🔴",
                FilePriority.HIGH: "🟠", 
                FilePriority.MEDIUM: "🟡",
                FilePriority.LOW: "🟢",
            }.get(priority, "⚪")
            status_emoji = {"added": "🆕", "modified": "📝", "deleted": "🗑️", "renamed": "📋"}.get(f.status, "📄")
            content_parts.append(f"- {priority_emoji}{status_emoji} `{f.filename}` (+{f.additions} -{f.deletions})")
        content_parts.append("")
        
        # 代码Diff
        content_parts.append("## 代码变更 (Diff)")
        for f in files:
            if f.patch:
                content_parts.append(f"\n### {f.filename}")
                content_parts.append("```diff")
                patch = f.patch
                if len(patch) > 4000:
                    patch = patch[:4000] + "\n... (内容截断)"
                content_parts.append(patch)
                content_parts.append("```")
        
        return "\n".join(content_parts)
    
    def _parse_review_response(self, response_text: str) -> Dict:
        """解析AI响应"""
        try:
            text = response_text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            return json.loads(text)
        except json.JSONDecodeError as e:
            return {
                "score": 50,
                "summary": f"审查结果解析失败: {str(e)}",
                "issues": [],
                "highlights": [],
                "suggestions": ["AI返回的结果格式异常，请重试"]
            }
    
    async def _call_model(self, content: str) -> str:
        """调用AI模型 - 根据provider路由到不同的API"""
        user_message = f"请审查以下Pull Request:\n\n{content}"
        
        if self.config.provider == ModelProvider.ANTHROPIC:
            return await self._call_anthropic(user_message)
        elif self.config.provider == ModelProvider.GEMINI:
            return await self._call_gemini(user_message)
        else:
            # OpenAI / DeepSeek / Ollama / Custom 都走OpenAI兼容接口
            return await self._call_openai_compatible(user_message)
    
    async def _call_openai_compatible(self, user_message: str) -> str:
        """调用OpenAI兼容接口 (OpenAI/DeepSeek/Ollama/Custom)"""
        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=self.config.temperature,
            max_tokens=4000
        )
        return response.choices[0].message.content
    
    async def _call_anthropic(self, user_message: str) -> str:
        """调用Anthropic Claude API"""
        response = await self.anthropic_client.messages.create(
            model=self.config.model,
            max_tokens=4000,
            temperature=self.config.temperature,
            system=self.SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )
        # Claude返回的content是一个列表
        return response.content[0].text
    
    async def _call_gemini(self, user_message: str) -> str:
        """调用Google Gemini API"""
        full_prompt = f"{self.SYSTEM_PROMPT}\n\n{user_message}"
        response = await self.gemini_client.aio.models.generate_content(
            model=self.config.model,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=self.config.temperature,
                max_output_tokens=4000,
            ),
        )
        return response.text
    
    async def review(
        self, 
        pr: PullRequest,
        github_token: Optional[str] = None,  # 用于获取完整文件内容
        owner: Optional[str] = None,
        repo: Optional[str] = None
    ) -> ReviewResult:
        """执行代码审查（增强版）"""
        
        if not pr.files:
            return ReviewResult(
                score=100,
                summary="没有代码变更需要审查",
                issues=[],
                highlights=[],
                suggestions=[]
            )
        
        # Step 1: 安全过滤
        filtered_files, sensitive_matches = self._filter_sensitive_content(pr.files)
        
        # 记录被过滤的敏感信息
        filtered_secrets = [
            {"type": m.type.value, "file": m.file, "line": m.line_number}
            for m in sensitive_matches
        ]
        
        # Step 2: 分片处理
        if self.config.enable_chunking and len(filtered_files) > self.config.max_files_per_chunk:
            chunks = self.chunker.create_chunks(filtered_files)
        else:
            chunks = [ReviewChunk(
                chunk_id=1,
                files=filtered_files,
                total_lines=sum(f.additions + f.deletions for f in filtered_files),
                estimated_tokens=0,
                priority=FilePriority.HIGH
            )]
        
        # 获取跳过的文件列表
        skipped_files = [
            f.filename for f in pr.files 
            if FileClassifier.get_priority(f) == FilePriority.SKIP
        ]
        
        # Step 3: 上下文增强（可选）
        context = None
        if (self.config.enable_context_enhancement and 
            github_token and owner and repo):
            try:
                enhancer = ContextEnhancer(github_token)
                file_dicts = [{"filename": f.filename, "status": f.status} for f in filtered_files]
                context = await enhancer.get_full_context(owner, repo, file_dicts, pr.head_ref)
            except Exception as e:
                # 上下文获取失败不影响主流程
                print(f"Warning: Failed to get context: {e}")
        
        # Step 4: 执行审查
        try:
            if len(chunks) == 1:
                # 单分片直接审查
                review_content = self._prepare_review_content(pr, chunks[0].files, context)
                response_text = await self._call_model(review_content)
                result_data = self._parse_review_response(response_text)
                
                issues = [
                    ReviewIssue(
                        severity=i.get("severity", "info"),
                        category=i.get("category", "style"),
                        file=i.get("file", "unknown"),
                        line=i.get("line"),
                        description=i.get("description", ""),
                        suggestion=i.get("suggestion")
                    )
                    for i in result_data.get("issues", [])
                ]
                
                return ReviewResult(
                    score=result_data.get("score", 70),
                    summary=result_data.get("summary", "审查完成"),
                    issues=issues,
                    highlights=result_data.get("highlights", []),
                    suggestions=result_data.get("suggestions", []),
                    filtered_secrets=filtered_secrets,
                    chunks_count=1,
                    skipped_files=skipped_files,
                    context_enhanced=context is not None
                )
            else:
                # 多分片逐个审查
                chunk_results = []
                for chunk in chunks:
                    review_content = self._prepare_review_content(pr, chunk.files, None)
                    response_text = await self._call_model(review_content)
                    result_data = self._parse_review_response(response_text)
                    
                    chunk_results.append(ChunkReviewResult(
                        chunk_id=chunk.chunk_id,
                        score=result_data.get("score", 70),
                        issues=result_data.get("issues", []),
                        summary=result_data.get("summary", "")
                    ))
                
                # 聚合结果
                aggregated = aggregate_chunk_reviews(
                    chunk_results, 
                    skipped_files, 
                    len(pr.files)
                )
                
                # 合并所有issues
                all_issues = []
                for cr in chunk_results:
                    for i in cr.issues:
                        all_issues.append(ReviewIssue(
                            severity=i.get("severity", "info"),
                            category=i.get("category", "style"),
                            file=i.get("file", "unknown"),
                            line=i.get("line"),
                            description=i.get("description", ""),
                            suggestion=i.get("suggestion")
                        ))
                
                return ReviewResult(
                    score=aggregated.overall_score,
                    summary=f"{aggregated.summary}。共发现{aggregated.total_issues}个问题。",
                    issues=all_issues,
                    highlights=[],
                    suggestions=[],
                    filtered_secrets=filtered_secrets,
                    chunks_count=len(chunks),
                    skipped_files=skipped_files,
                    context_enhanced=False
                )
                
        except Exception as e:
            return ReviewResult(
                score=0,
                summary=f"审查过程出错: {str(e)}",
                issues=[],
                highlights=[],
                suggestions=["请检查API配置后重试"],
                filtered_secrets=filtered_secrets,
                skipped_files=skipped_files
            )
    
    # 保留旧接口的兼容性
    async def review_simple(self, pr: PullRequest, model: str = "gpt-4o") -> ReviewResult:
        """简单审查模式（兼容旧接口）"""
        self.config.model = model
        self.config.enable_context_enhancement = False
        return await self.review(pr)
