"""
AI Code Reviewer - 大PR处理模块
智能分片、优先级排序、增量审查
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from github_client import FileChange, PullRequest


class FilePriority(str, Enum):
    """文件优先级"""
    CRITICAL = "critical"    # 核心业务代码
    HIGH = "high"           # 重要代码
    MEDIUM = "medium"       # 普通代码
    LOW = "low"             # 低优先级
    SKIP = "skip"           # 跳过不审查


@dataclass
class FileGroup:
    """文件分组"""
    name: str
    description: str
    files: List[FileChange] = field(default_factory=list)
    total_changes: int = 0
    priority: FilePriority = FilePriority.MEDIUM


@dataclass
class ReviewChunk:
    """审查分片"""
    chunk_id: int
    files: List[FileChange]
    total_lines: int
    estimated_tokens: int
    priority: FilePriority


class FileClassifier:
    """文件分类器"""
    
    # 应该跳过的文件模式
    SKIP_PATTERNS = [
        r'package-lock\.json$',
        r'yarn\.lock$',
        r'pnpm-lock\.yaml$',
        r'Cargo\.lock$',
        r'poetry\.lock$',
        r'go\.sum$',
        r'\.min\.js$',
        r'\.min\.css$',
        r'\.map$',
        r'\.d\.ts$',  # TypeScript声明文件
        r'\.generated\.',
        r'__generated__',
        r'\.snap$',  # Jest快照
        r'\.svg$',
        r'\.png$',
        r'\.jpg$',
        r'\.gif$',
        r'\.ico$',
        r'\.woff',
        r'\.ttf$',
        r'\.eot$',
        r'dist/',
        r'build/',
        r'node_modules/',
        r'vendor/',
        r'\.git/',
    ]
    
    # 高优先级文件模式 (核心业务代码)
    CRITICAL_PATTERNS = [
        r'src/.*\.(py|js|ts|java|go|rs)$',
        r'app/.*\.(py|js|ts|java|go|rs)$',
        r'lib/.*\.(py|js|ts|java|go|rs)$',
        r'core/.*\.(py|js|ts|java|go|rs)$',
        r'api/.*\.(py|js|ts|java|go|rs)$',
        r'services?/.*\.(py|js|ts|java|go|rs)$',
        r'controllers?/.*\.(py|js|ts|java|go|rs)$',
        r'models?/.*\.(py|js|ts|java|go|rs)$',
        r'handlers?/.*\.(py|js|ts|java|go|rs)$',
    ]
    
    # 安全敏感文件
    SECURITY_PATTERNS = [
        r'auth',
        r'login',
        r'password',
        r'permission',
        r'security',
        r'crypto',
        r'encrypt',
        r'token',
        r'secret',
        r'credential',
    ]
    
    # 配置文件
    CONFIG_PATTERNS = [
        r'\.env',
        r'config\.',
        r'settings\.',
        r'\.ya?ml$',
        r'\.json$',
        r'\.toml$',
        r'\.ini$',
        r'Dockerfile',
        r'docker-compose',
        r'\.github/',
        r'\.gitlab-ci',
        r'Makefile',
    ]
    
    # 测试文件
    TEST_PATTERNS = [
        r'test[s_]?/',
        r'spec[s]?/',
        r'__tests__/',
        r'\.test\.',
        r'\.spec\.',
        r'_test\.',
        r'_spec\.',
        r'test_.*\.py$',
        r'.*_test\.go$',
    ]
    
    @classmethod
    def should_skip(cls, filename: str) -> bool:
        """判断是否应该跳过该文件"""
        for pattern in cls.SKIP_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def get_priority(cls, file: FileChange) -> FilePriority:
        """获取文件的优先级"""
        filename = file.filename.lower()
        
        # 跳过的文件
        if cls.should_skip(filename):
            return FilePriority.SKIP
        
        # 安全敏感文件 - 最高优先级
        for pattern in cls.SECURITY_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                return FilePriority.CRITICAL
        
        # 核心业务代码
        for pattern in cls.CRITICAL_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                # 变更行数多的更重要
                if file.additions + file.deletions > 50:
                    return FilePriority.CRITICAL
                return FilePriority.HIGH
        
        # 配置文件
        for pattern in cls.CONFIG_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                return FilePriority.MEDIUM
        
        # 测试文件
        for pattern in cls.TEST_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                return FilePriority.LOW
        
        # 默认中等优先级
        return FilePriority.MEDIUM
    
    @classmethod
    def get_file_type_group(cls, filename: str) -> str:
        """获取文件所属的类型分组"""
        lower = filename.lower()
        
        # 测试文件
        for pattern in cls.TEST_PATTERNS:
            if re.search(pattern, lower):
                return "test"
        
        # 配置文件
        for pattern in cls.CONFIG_PATTERNS:
            if re.search(pattern, lower):
                return "config"
        
        # 文档
        if re.search(r'\.(md|rst|txt|doc)$', lower):
            return "docs"
        
        # 前端代码
        if re.search(r'\.(jsx?|tsx?|vue|svelte|css|scss|less|html)$', lower):
            return "frontend"
        
        # 后端代码
        if re.search(r'\.(py|java|go|rs|rb|php|cs)$', lower):
            return "backend"
        
        return "other"


class PRChunker:
    """PR分片器 - 将大PR拆分成可处理的小块"""
    
    # 估算：平均每行代码约10个token
    TOKENS_PER_LINE = 10
    # 单次审查的最大token数 (给模型留余量)
    MAX_TOKENS_PER_CHUNK = 8000
    # 单次审查的最大文件数
    MAX_FILES_PER_CHUNK = 15
    
    def __init__(
        self,
        max_tokens: int = MAX_TOKENS_PER_CHUNK,
        max_files: int = MAX_FILES_PER_CHUNK
    ):
        self.max_tokens = max_tokens
        self.max_files = max_files
    
    def estimate_tokens(self, file: FileChange) -> int:
        """估算文件的token数"""
        lines = file.additions + file.deletions
        # patch内容的实际长度
        patch_tokens = len(file.patch or "") // 4 if file.patch else 0
        return max(lines * self.TOKENS_PER_LINE, patch_tokens)
    
    def classify_and_sort(self, files: List[FileChange]) -> List[FileChange]:
        """分类并按优先级排序文件"""
        # 过滤掉应该跳过的文件
        filtered = [f for f in files if FileClassifier.get_priority(f) != FilePriority.SKIP]
        
        # 按优先级排序
        priority_order = {
            FilePriority.CRITICAL: 0,
            FilePriority.HIGH: 1,
            FilePriority.MEDIUM: 2,
            FilePriority.LOW: 3,
        }
        
        return sorted(filtered, key=lambda f: (
            priority_order.get(FileClassifier.get_priority(f), 99),
            -(f.additions + f.deletions)  # 变更多的优先
        ))
    
    def create_chunks(self, files: List[FileChange]) -> List[ReviewChunk]:
        """将文件列表分成多个审查分片"""
        sorted_files = self.classify_and_sort(files)
        chunks = []
        current_files = []
        current_tokens = 0
        chunk_id = 1
        
        for file in sorted_files:
            file_tokens = self.estimate_tokens(file)
            
            # 检查是否需要开始新的分片
            if (current_tokens + file_tokens > self.max_tokens or 
                len(current_files) >= self.max_files) and current_files:
                # 保存当前分片
                chunks.append(self._create_chunk(chunk_id, current_files, current_tokens))
                chunk_id += 1
                current_files = []
                current_tokens = 0
            
            current_files.append(file)
            current_tokens += file_tokens
        
        # 保存最后一个分片
        if current_files:
            chunks.append(self._create_chunk(chunk_id, current_files, current_tokens))
        
        return chunks
    
    def _create_chunk(
        self, 
        chunk_id: int, 
        files: List[FileChange], 
        tokens: int
    ) -> ReviewChunk:
        """创建审查分片"""
        # 分片优先级取文件中最高的
        priorities = [FileClassifier.get_priority(f) for f in files]
        chunk_priority = min(priorities, key=lambda p: {
            FilePriority.CRITICAL: 0,
            FilePriority.HIGH: 1,
            FilePriority.MEDIUM: 2,
            FilePriority.LOW: 3,
            FilePriority.SKIP: 4,
        }.get(p, 99))
        
        total_lines = sum(f.additions + f.deletions for f in files)
        
        return ReviewChunk(
            chunk_id=chunk_id,
            files=files,
            total_lines=total_lines,
            estimated_tokens=tokens,
            priority=chunk_priority
        )
    
    def group_by_type(self, files: List[FileChange]) -> Dict[str, FileGroup]:
        """按文件类型分组"""
        groups: Dict[str, FileGroup] = {
            "backend": FileGroup("backend", "后端代码"),
            "frontend": FileGroup("frontend", "前端代码"),
            "test": FileGroup("test", "测试代码"),
            "config": FileGroup("config", "配置文件"),
            "docs": FileGroup("docs", "文档"),
            "other": FileGroup("other", "其他文件"),
        }
        
        for file in files:
            if FileClassifier.should_skip(file.filename):
                continue
            
            group_name = FileClassifier.get_file_type_group(file.filename)
            if group_name in groups:
                groups[group_name].files.append(file)
                groups[group_name].total_changes += file.additions + file.deletions
        
        # 设置分组优先级
        priority_map = {
            "backend": FilePriority.CRITICAL,
            "frontend": FilePriority.HIGH,
            "config": FilePriority.HIGH,
            "test": FilePriority.MEDIUM,
            "docs": FilePriority.LOW,
            "other": FilePriority.LOW,
        }
        for name, group in groups.items():
            group.priority = priority_map.get(name, FilePriority.MEDIUM)
        
        return {k: v for k, v in groups.items() if v.files}


@dataclass
class ChunkReviewResult:
    """分片审查结果"""
    chunk_id: int
    score: int
    issues: List[Dict]
    summary: str


@dataclass
class AggregatedReview:
    """聚合的审查结果"""
    overall_score: int
    summary: str
    chunk_results: List[ChunkReviewResult]
    total_issues: int
    issues_by_severity: Dict[str, int]
    skipped_files: List[str]
    review_coverage: float  # 审查覆盖率


def aggregate_chunk_reviews(
    chunk_results: List[ChunkReviewResult],
    skipped_files: List[str],
    total_files: int
) -> AggregatedReview:
    """聚合多个分片的审查结果"""
    
    if not chunk_results:
        return AggregatedReview(
            overall_score=0,
            summary="没有可审查的内容",
            chunk_results=[],
            total_issues=0,
            issues_by_severity={},
            skipped_files=skipped_files,
            review_coverage=0.0
        )
    
    # 计算加权平均分
    total_score = sum(r.score for r in chunk_results)
    overall_score = total_score // len(chunk_results)
    
    # 汇总所有问题
    all_issues = []
    issues_by_severity = {"critical": 0, "major": 0, "minor": 0, "info": 0}
    
    for result in chunk_results:
        all_issues.extend(result.issues)
        for issue in result.issues:
            severity = issue.get("severity", "info")
            if severity in issues_by_severity:
                issues_by_severity[severity] += 1
    
    # 生成总结
    summary_parts = [f"共审查了{len(chunk_results)}个分片"]
    if issues_by_severity["critical"] > 0:
        summary_parts.append(f"发现{issues_by_severity['critical']}个严重问题")
    if issues_by_severity["major"] > 0:
        summary_parts.append(f"{issues_by_severity['major']}个重要问题")
    
    # 计算覆盖率
    reviewed_files = sum(len(r.issues) > 0 or r.score > 0 for r in chunk_results)
    coverage = (total_files - len(skipped_files)) / total_files if total_files > 0 else 0
    
    return AggregatedReview(
        overall_score=overall_score,
        summary="；".join(summary_parts),
        chunk_results=chunk_results,
        total_issues=len(all_issues),
        issues_by_severity=issues_by_severity,
        skipped_files=skipped_files,
        review_coverage=coverage
    )
