"""
AI Code Reviewer - GitHub API Client
用于与GitHub API交互的客户端模块
"""

import httpx
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum


class PRState(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    ALL = "all"


@dataclass
class GitHubUser:
    login: str
    name: Optional[str]
    avatar_url: str
    html_url: str


@dataclass
class Repository:
    full_name: str
    name: str
    owner: str
    description: Optional[str]
    private: bool
    html_url: str
    default_branch: str


@dataclass
class FileChange:
    filename: str
    status: str  # added, modified, deleted, renamed
    additions: int
    deletions: int
    changes: int
    patch: Optional[str]  # diff内容


@dataclass
class PullRequest:
    number: int
    title: str
    body: Optional[str]
    state: str
    author: str
    author_avatar: str
    html_url: str
    created_at: str
    updated_at: str
    head_ref: str
    base_ref: str
    additions: int
    deletions: int
    changed_files: int
    files: Optional[List[FileChange]] = None
    diff: Optional[str] = None


class GitHubClient:
    """GitHub API客户端"""
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
    
    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Any:
        """发送HTTP请求"""
        url = f"{self.BASE_URL}{endpoint}"
        request_headers = {**self.headers}
        if headers:
            request_headers.update(headers)
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                headers=request_headers,
                timeout=30.0
            )
            
            if response.status_code == 401:
                raise Exception("GitHub Token无效或已过期")
            elif response.status_code == 403:
                raise Exception("API请求次数超限或权限不足")
            elif response.status_code == 404:
                raise Exception("资源不存在")
            elif response.status_code >= 400:
                raise Exception(f"GitHub API错误: {response.status_code}")
            
            # 检查是否是diff格式
            content_type = response.headers.get("content-type", "")
            if "text/plain" in content_type or "application/vnd.github.v3.diff" in content_type:
                return response.text
            
            return response.json()
    
    async def validate_token(self) -> GitHubUser:
        """验证Token并获取用户信息"""
        data = await self._request("GET", "/user")
        return GitHubUser(
            login=data["login"],
            name=data.get("name"),
            avatar_url=data["avatar_url"],
            html_url=data["html_url"]
        )
    
    async def get_repos(self, per_page: int = 30, page: int = 1) -> List[Repository]:
        """获取用户可访问的仓库列表"""
        data = await self._request(
            "GET", 
            "/user/repos",
            params={
                "per_page": per_page,
                "page": page,
                "sort": "updated",
                "direction": "desc"
            }
        )
        
        repos = []
        for repo in data:
            repos.append(Repository(
                full_name=repo["full_name"],
                name=repo["name"],
                owner=repo["owner"]["login"],
                description=repo.get("description"),
                private=repo["private"],
                html_url=repo["html_url"],
                default_branch=repo.get("default_branch", "main")
            ))
        return repos
    
    async def get_pull_requests(
        self, 
        owner: str, 
        repo: str, 
        state: PRState = PRState.OPEN,
        per_page: int = 20
    ) -> List[PullRequest]:
        """获取仓库的PR列表"""
        data = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/pulls",
            params={
                "state": state.value,
                "per_page": per_page,
                "sort": "updated",
                "direction": "desc"
            }
        )
        
        prs = []
        for pr in data:
            prs.append(PullRequest(
                number=pr["number"],
                title=pr["title"],
                body=pr.get("body"),
                state=pr["state"],
                author=pr["user"]["login"],
                author_avatar=pr["user"]["avatar_url"],
                html_url=pr["html_url"],
                created_at=pr["created_at"],
                updated_at=pr["updated_at"],
                head_ref=pr["head"]["ref"],
                base_ref=pr["base"]["ref"],
                additions=0,
                deletions=0,
                changed_files=0
            ))
        return prs
    
    async def get_pull_request_detail(
        self, 
        owner: str, 
        repo: str, 
        pull_number: int
    ) -> PullRequest:
        """获取单个PR的详细信息"""
        # 获取PR基本信息
        pr_data = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/pulls/{pull_number}"
        )
        
        # 获取PR的文件变更
        files_data = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/pulls/{pull_number}/files"
        )
        
        files = []
        for f in files_data:
            files.append(FileChange(
                filename=f["filename"],
                status=f["status"],
                additions=f["additions"],
                deletions=f["deletions"],
                changes=f["changes"],
                patch=f.get("patch")
            ))
        
        # 获取完整diff
        diff = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/pulls/{pull_number}",
            headers={"Accept": "application/vnd.github.v3.diff"}
        )
        
        return PullRequest(
            number=pr_data["number"],
            title=pr_data["title"],
            body=pr_data.get("body"),
            state=pr_data["state"],
            author=pr_data["user"]["login"],
            author_avatar=pr_data["user"]["avatar_url"],
            html_url=pr_data["html_url"],
            created_at=pr_data["created_at"],
            updated_at=pr_data["updated_at"],
            head_ref=pr_data["head"]["ref"],
            base_ref=pr_data["base"]["ref"],
            additions=pr_data.get("additions", 0),
            deletions=pr_data.get("deletions", 0),
            changed_files=pr_data.get("changed_files", 0),
            files=files,
            diff=diff if isinstance(diff, str) else None
        )
