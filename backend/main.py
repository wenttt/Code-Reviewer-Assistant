"""
AI Code Reviewer - FastAPI Backend (Enhanced)
主应用入口 - 增强版
"""

import os
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from github_client import GitHubClient, PRState
from ai_reviewer import AIReviewEngine, ReviewConfig, ModelProvider
from security import SensitiveFilter, has_sensitive_info
from chunker import PRChunker, FileClassifier

# 加载环境变量
load_dotenv()

app = FastAPI(
    title="AI Code Reviewer API",
    description="智能代码审查服务API - 增强版 (支持多模型提供商)",
    version="3.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ================== 请求/响应模型 ==================

class TokenValidateRequest(BaseModel):
    token: str


class TokenValidateResponse(BaseModel):
    valid: bool
    user: Optional[dict] = None
    error: Optional[str] = None


class ReviewRequest(BaseModel):
    owner: str
    repo: str
    pull_number: int
    openai_api_key: str = ""
    openai_base_url: Optional[str] = None
    # 配置选项
    enable_security_filter: bool = True
    enable_context_enhancement: bool = True
    model: str = "gpt-4o"
    provider: str = "openai"  # openai | deepseek | anthropic | gemini | ollama | custom
    ollama_base_url: Optional[str] = None
    # 自定义API设置
    custom_base_url: Optional[str] = None
    custom_model_name: Optional[str] = None


class ReviewResponse(BaseModel):
    success: bool
    review: Optional[dict] = None
    error: Optional[str] = None
    # 新增元信息
    meta: Optional[dict] = None


class SecurityCheckRequest(BaseModel):
    content: str
    filename: Optional[str] = None


class SecurityCheckResponse(BaseModel):
    has_sensitive: bool
    matches: List[dict] = []
    filtered_content: Optional[str] = None


class PRAnalyzeResponse(BaseModel):
    total_files: int
    reviewable_files: int
    skipped_files: List[str]
    chunks_needed: int
    estimated_time: str
    file_groups: dict


# ================== 辅助函数 ==================

def get_github_token(authorization: str = Header(None)) -> str:
    """从请求头获取GitHub Token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未提供认证信息")
    
    if authorization.startswith("Bearer "):
        return authorization[7:]
    return authorization


# ================== API路由 ==================

@app.get("/")
async def root():
    """健康检查"""
    return {
        "status": "ok", 
        "message": "AI Code Reviewer API is running",
        "version": "3.0.0",
        "features": [
            "sensitive_info_filter",
            "large_pr_chunking", 
            "context_enhancement",
            "local_model_support",
            "multi_provider_support",
            "custom_api_support"
        ]
    }


@app.post("/api/auth/validate", response_model=TokenValidateResponse)
async def validate_token(request: TokenValidateRequest):
    """验证GitHub Token"""
    try:
        client = GitHubClient(request.token)
        user = await client.validate_token()
        return TokenValidateResponse(
            valid=True,
            user={
                "login": user.login,
                "name": user.name,
                "avatar_url": user.avatar_url,
                "html_url": user.html_url
            }
        )
    except Exception as e:
        return TokenValidateResponse(
            valid=False,
            error=str(e)
        )


@app.get("/api/repos")
async def get_repos(authorization: str = Header(None)):
    """获取用户的仓库列表"""
    token = get_github_token(authorization)
    try:
        client = GitHubClient(token)
        repos = await client.get_repos(per_page=50)
        return {
            "repos": [
                {
                    "full_name": repo.full_name,
                    "name": repo.name,
                    "owner": repo.owner,
                    "description": repo.description,
                    "private": repo.private,
                    "html_url": repo.html_url
                }
                for repo in repos
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/repos/{owner}/{repo}/pulls")
async def get_pull_requests(
    owner: str, 
    repo: str, 
    state: str = "open",
    authorization: str = Header(None)
):
    """获取仓库的PR列表"""
    token = get_github_token(authorization)
    try:
        client = GitHubClient(token)
        pr_state = PRState(state) if state in ["open", "closed", "all"] else PRState.OPEN
        prs = await client.get_pull_requests(owner, repo, state=pr_state)
        return {
            "pulls": [
                {
                    "number": pr.number,
                    "title": pr.title,
                    "state": pr.state,
                    "author": pr.author,
                    "author_avatar": pr.author_avatar,
                    "html_url": pr.html_url,
                    "created_at": pr.created_at,
                    "updated_at": pr.updated_at,
                    "head_ref": pr.head_ref,
                    "base_ref": pr.base_ref
                }
                for pr in prs
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/repos/{owner}/{repo}/pulls/{pull_number}")
async def get_pull_request_detail(
    owner: str, 
    repo: str, 
    pull_number: int,
    authorization: str = Header(None)
):
    """获取单个PR的详细信息"""
    token = get_github_token(authorization)
    try:
        client = GitHubClient(token)
        pr = await client.get_pull_request_detail(owner, repo, pull_number)
        return {
            "pr": {
                "number": pr.number,
                "title": pr.title,
                "body": pr.body,
                "state": pr.state,
                "author": pr.author,
                "author_avatar": pr.author_avatar,
                "html_url": pr.html_url,
                "created_at": pr.created_at,
                "updated_at": pr.updated_at,
                "head_ref": pr.head_ref,
                "base_ref": pr.base_ref,
                "additions": pr.additions,
                "deletions": pr.deletions,
                "changed_files": pr.changed_files,
                "files": [
                    {
                        "filename": f.filename,
                        "status": f.status,
                        "additions": f.additions,
                        "deletions": f.deletions,
                        "patch": f.patch
                    }
                    for f in (pr.files or [])
                ]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/repos/{owner}/{repo}/pulls/{pull_number}/analyze", response_model=PRAnalyzeResponse)
async def analyze_pr(
    owner: str,
    repo: str,
    pull_number: int,
    authorization: str = Header(None)
):
    """分析PR的复杂度和审查计划（预览功能）"""
    token = get_github_token(authorization)
    try:
        client = GitHubClient(token)
        pr = await client.get_pull_request_detail(owner, repo, pull_number)
        
        if not pr.files:
            return PRAnalyzeResponse(
                total_files=0,
                reviewable_files=0,
                skipped_files=[],
                chunks_needed=0,
                estimated_time="0分钟",
                file_groups={}
            )
        
        # 分析文件
        chunker = PRChunker()
        chunks = chunker.create_chunks(pr.files)
        groups = chunker.group_by_type(pr.files)
        
        skipped = [f.filename for f in pr.files if FileClassifier.should_skip(f.filename)]
        reviewable = len(pr.files) - len(skipped)
        
        # 估算时间：每个分片约30秒
        estimated_minutes = len(chunks) * 0.5
        if estimated_minutes < 1:
            estimated_time = "少于1分钟"
        else:
            estimated_time = f"约{int(estimated_minutes)}分钟"
        
        return PRAnalyzeResponse(
            total_files=len(pr.files),
            reviewable_files=reviewable,
            skipped_files=skipped,
            chunks_needed=len(chunks),
            estimated_time=estimated_time,
            file_groups={
                name: {
                    "count": len(group.files),
                    "changes": group.total_changes,
                    "priority": group.priority.value
                }
                for name, group in groups.items()
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/security/check", response_model=SecurityCheckResponse)
async def check_sensitive_info(request: SecurityCheckRequest):
    """检查内容中的敏感信息"""
    filter = SensitiveFilter()
    filtered_content, matches = filter.filter_content(request.content, request.filename or "")
    
    return SecurityCheckResponse(
        has_sensitive=len(matches) > 0,
        matches=[
            {
                "type": m.type.value,
                "line": m.line_number,
                "masked": m.masked
            }
            for m in matches
        ],
        filtered_content=filtered_content if matches else None
    )


@app.post("/api/review", response_model=ReviewResponse)
async def perform_review(
    request: ReviewRequest,
    authorization: str = Header(None)
):
    """执行AI代码审查（增强版 - 支持多模型提供商）"""
    token = get_github_token(authorization)
    
    try:
        # 获取PR详情
        github_client = GitHubClient(token)
        pr = await github_client.get_pull_request_detail(
            request.owner, 
            request.repo, 
            request.pull_number
        )
        
        # 构建审查配置
        valid_providers = ["openai", "deepseek", "anthropic", "gemini", "ollama", "custom"]
        provider = request.provider if request.provider in valid_providers else "openai"
        
        config = ReviewConfig(
            enable_security_filter=request.enable_security_filter,
            enable_context_enhancement=request.enable_context_enhancement,
            model=request.model,
            provider=ModelProvider(provider),
        )
        
        # 各 provider 特殊配置
        if provider == "ollama" and request.ollama_base_url:
            config.ollama_base_url = request.ollama_base_url
        
        if provider == "custom":
            if request.custom_base_url:
                config.custom_base_url = request.custom_base_url
            if request.custom_model_name:
                config.custom_model_name = request.custom_model_name
                config.model = request.custom_model_name
        
        # 确定 base_url
        base_url = request.openai_base_url
        if provider == "custom" and request.custom_base_url:
            base_url = request.custom_base_url
        
        # 初始化AI审查引擎
        ai_engine = AIReviewEngine(
            api_key=request.openai_api_key,
            base_url=base_url,
            config=config
        )
        
        # 执行审查（带上下文增强）
        result = await ai_engine.review(
            pr,
            github_token=token,
            owner=request.owner,
            repo=request.repo
        )
        
        return ReviewResponse(
            success=True,
            review=result.to_dict(),
            meta={
                "provider": provider,
                "model": config.model,
                "chunks_count": result.chunks_count,
                "context_enhanced": result.context_enhanced,
                "security_filtered": len(result.filtered_secrets or []) > 0,
                "skipped_files_count": len(result.skipped_files or [])
            }
        )
    except Exception as e:
        return ReviewResponse(
            success=False,
            error=str(e)
        )


# ================== 模型配置相关 ==================

@app.get("/api/models/providers")
async def get_model_providers():
    """获取支持的模型提供商列表"""
    return {
        "providers": [
            {
                "id": "deepseek",
                "name": "DeepSeek",
                "description": "DeepSeek AI - 高性价比的代码专用模型",
                "models": ["deepseek-chat", "deepseek-coder", "deepseek-reasoner"],
                "requires_api_key": True,
                "supports_base_url": True,
                "default_base_url": "https://api.deepseek.com"
            },
            {
                "id": "openai",
                "name": "OpenAI",
                "description": "OpenAI GPT系列模型",
                "models": ["gpt-5", "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano", "o3", "o4-mini", "gpt-4o", "gpt-4o-mini"],
                "requires_api_key": True,
                "supports_base_url": True
            },
            {
                "id": "anthropic",
                "name": "Anthropic Claude",
                "description": "Anthropic Claude系列 - 代码审查能力强，安全可控",
                "models": ["claude-sonnet-4-20250514", "claude-opus-4-20250514", "claude-3-7-sonnet-latest", "claude-3-5-haiku-latest"],
                "requires_api_key": True,
                "supports_base_url": True,
                "default_base_url": "https://api.anthropic.com"
            },
            {
                "id": "gemini",
                "name": "Google Gemini",
                "description": "Google Gemini系列 - 多模态大模型，长上下文窗口",
                "models": ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"],
                "requires_api_key": True,
                "supports_base_url": False
            },
            {
                "id": "ollama", 
                "name": "Ollama (本地)",
                "description": "本地部署的开源模型，数据不出本地",
                "models": ["qwen3", "deepseek-r1", "codellama", "llama4", "gemma3", "devstral"],
                "requires_api_key": False,
                "supports_base_url": True,
                "default_base_url": "http://localhost:11434"
            },
            {
                "id": "custom",
                "name": "自定义API",
                "description": "接入公司内部或第三方AI服务 (兼容OpenAI接口)",
                "models": [],
                "requires_api_key": True,
                "supports_base_url": True,
                "allow_custom_model": True
            }
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
