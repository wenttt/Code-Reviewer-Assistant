"""
AI Code Reviewer - 安全模块
敏感信息检测和过滤
"""

import re
from typing import List, Tuple, Dict, Set
from dataclasses import dataclass
from enum import Enum


class SensitiveType(str, Enum):
    API_KEY = "api_key"
    PASSWORD = "password"
    TOKEN = "token"
    SECRET = "secret"
    PRIVATE_KEY = "private_key"
    CONNECTION_STRING = "connection_string"
    EMAIL = "email"
    IP_ADDRESS = "ip_address"
    AWS_CREDENTIAL = "aws_credential"


@dataclass
class SensitiveMatch:
    """敏感信息匹配结果"""
    type: SensitiveType
    original: str
    masked: str
    line_number: int
    file: str


class SensitiveFilter:
    """敏感信息过滤器"""
    
    # 敏感信息正则表达式模式
    PATTERNS: Dict[SensitiveType, List[re.Pattern]] = {
        SensitiveType.API_KEY: [
            re.compile(r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?'),
            re.compile(r'(?i)sk-[a-zA-Z0-9]{20,}'),  # OpenAI API Key
            re.compile(r'(?i)ghp_[a-zA-Z0-9]{36}'),  # GitHub Personal Token
            re.compile(r'(?i)gho_[a-zA-Z0-9]{36}'),  # GitHub OAuth Token
            re.compile(r'(?i)github_pat_[a-zA-Z0-9_]{22,}'),  # GitHub Fine-grained Token
        ],
        SensitiveType.PASSWORD: [
            re.compile(r'(?i)(password|passwd|pwd)\s*[=:]\s*["\']?([^\s"\']{6,})["\']?'),
            re.compile(r'(?i)(db_pass|database_password|mysql_pwd)\s*[=:]\s*["\']?([^\s"\']+)["\']?'),
        ],
        SensitiveType.TOKEN: [
            re.compile(r'(?i)(access[_-]?token|auth[_-]?token|bearer)\s*[=:]\s*["\']?([a-zA-Z0-9_\-\.]{20,})["\']?'),
            re.compile(r'(?i)eyJ[a-zA-Z0-9_\-]*\.eyJ[a-zA-Z0-9_\-]*\.[a-zA-Z0-9_\-]*'),  # JWT Token
        ],
        SensitiveType.SECRET: [
            re.compile(r'(?i)(secret|client[_-]?secret|app[_-]?secret)\s*[=:]\s*["\']?([a-zA-Z0-9_\-]{16,})["\']?'),
        ],
        SensitiveType.PRIVATE_KEY: [
            re.compile(r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----'),
            re.compile(r'-----BEGIN\s+OPENSSH\s+PRIVATE\s+KEY-----'),
            re.compile(r'-----BEGIN\s+EC\s+PRIVATE\s+KEY-----'),
        ],
        SensitiveType.CONNECTION_STRING: [
            re.compile(r'(?i)(mongodb|mysql|postgres|redis|amqp)://[^\s"\']+:[^\s"\']+@[^\s"\']+'),
            re.compile(r'(?i)Server\s*=\s*[^;]+;\s*Database\s*=\s*[^;]+;\s*User\s*Id\s*=\s*[^;]+;\s*Password\s*=\s*[^;]+'),
        ],
        SensitiveType.AWS_CREDENTIAL: [
            re.compile(r'(?i)AKIA[0-9A-Z]{16}'),  # AWS Access Key ID
            re.compile(r'(?i)(aws[_-]?secret[_-]?access[_-]?key)\s*[=:]\s*["\']?([a-zA-Z0-9/+=]{40})["\']?'),
        ],
        SensitiveType.IP_ADDRESS: [
            # 只匹配内网IP (可能是生产环境配置)
            re.compile(r'\b(10\.\d{1,3}\.\d{1,3}\.\d{1,3})\b'),
            re.compile(r'\b(172\.(1[6-9]|2[0-9]|3[01])\.\d{1,3}\.\d{1,3})\b'),
            re.compile(r'\b(192\.168\.\d{1,3}\.\d{1,3})\b'),
        ],
    }
    
    # 应该跳过的文件模式 (这些文件本身就是示例或文档)
    SKIP_FILE_PATTERNS = [
        r'\.example$',
        r'\.sample$',
        r'\.template$',
        r'README',
        r'CHANGELOG',
        r'\.md$',
        r'\.txt$',
        r'test.*\.py$',
        r'.*_test\.go$',
        r'.*\.test\.(js|ts)$',
    ]
    
    def __init__(self, custom_patterns: Dict[str, str] = None):
        """初始化过滤器
        
        Args:
            custom_patterns: 自定义敏感词模式 {名称: 正则表达式}
        """
        self.custom_patterns = {}
        if custom_patterns:
            for name, pattern in custom_patterns.items():
                self.custom_patterns[name] = re.compile(pattern)
    
    def should_skip_file(self, filename: str) -> bool:
        """判断是否应该跳过该文件的敏感检测"""
        for pattern in self.SKIP_FILE_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                return True
        return False
    
    def detect_sensitive(self, content: str, filename: str = "") -> List[SensitiveMatch]:
        """检测内容中的敏感信息
        
        Args:
            content: 要检测的内容
            filename: 文件名（用于记录和跳过判断）
            
        Returns:
            检测到的敏感信息列表
        """
        if self.should_skip_file(filename):
            return []
        
        matches = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            # 跳过注释行 (简单判断)
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('//') or stripped.startswith('*'):
                continue
            
            # 检测标准模式
            for sensitive_type, patterns in self.PATTERNS.items():
                for pattern in patterns:
                    for match in pattern.finditer(line):
                        matched_text = match.group(0)
                        masked_text = self._mask_sensitive(matched_text, sensitive_type)
                        matches.append(SensitiveMatch(
                            type=sensitive_type,
                            original=matched_text,
                            masked=masked_text,
                            line_number=line_num,
                            file=filename
                        ))
            
            # 检测自定义模式
            for name, pattern in self.custom_patterns.items():
                for match in pattern.finditer(line):
                    matched_text = match.group(0)
                    matches.append(SensitiveMatch(
                        type=SensitiveType.SECRET,
                        original=matched_text,
                        masked=f"[CUSTOM:{name}]***",
                        line_number=line_num,
                        file=filename
                    ))
        
        return matches
    
    def _mask_sensitive(self, text: str, sensitive_type: SensitiveType) -> str:
        """对敏感信息进行脱敏处理"""
        if sensitive_type == SensitiveType.PRIVATE_KEY:
            return "[PRIVATE_KEY_REDACTED]"
        
        if sensitive_type == SensitiveType.CONNECTION_STRING:
            # 保留协议和主机，隐藏密码
            return re.sub(r'://[^:]+:[^@]+@', '://***:***@', text)
        
        if sensitive_type == SensitiveType.IP_ADDRESS:
            # 部分隐藏IP
            return re.sub(r'(\d+\.\d+)\.\d+\.\d+', r'\1.***.***', text)
        
        # 通用处理：保留前后几个字符
        if len(text) > 10:
            return text[:4] + '*' * (len(text) - 8) + text[-4:]
        else:
            return text[:2] + '*' * (len(text) - 2)
    
    def filter_content(self, content: str, filename: str = "") -> Tuple[str, List[SensitiveMatch]]:
        """过滤内容中的敏感信息
        
        Args:
            content: 原始内容
            filename: 文件名
            
        Returns:
            (过滤后的内容, 检测到的敏感信息列表)
        """
        matches = self.detect_sensitive(content, filename)
        
        if not matches:
            return content, []
        
        filtered_content = content
        # 按原始文本长度倒序替换，避免位置偏移问题
        for match in sorted(matches, key=lambda m: len(m.original), reverse=True):
            filtered_content = filtered_content.replace(match.original, match.masked)
        
        return filtered_content, matches
    
    def filter_diff(self, diff: str, filename: str = "") -> Tuple[str, List[SensitiveMatch]]:
        """过滤diff内容中的敏感信息，保留diff格式"""
        return self.filter_content(diff, filename)


class SecurityConfig:
    """安全配置"""
    
    def __init__(
        self,
        enable_filter: bool = True,
        filter_mode: str = "mask",  # mask | warn | block
        exclude_files: List[str] = None,
        custom_patterns: Dict[str, str] = None,
        allow_local_only: bool = False,  # 只允许本地模型
    ):
        self.enable_filter = enable_filter
        self.filter_mode = filter_mode
        self.exclude_files = exclude_files or []
        self.custom_patterns = custom_patterns or {}
        self.allow_local_only = allow_local_only
    
    def to_dict(self):
        return {
            "enable_filter": self.enable_filter,
            "filter_mode": self.filter_mode,
            "exclude_files": self.exclude_files,
            "allow_local_only": self.allow_local_only
        }


# 全局默认过滤器实例
default_filter = SensitiveFilter()


def quick_filter(content: str, filename: str = "") -> Tuple[str, List[SensitiveMatch]]:
    """快速过滤敏感信息的便捷函数"""
    return default_filter.filter_content(content, filename)


def has_sensitive_info(content: str, filename: str = "") -> bool:
    """快速检测是否包含敏感信息"""
    matches = default_filter.detect_sensitive(content, filename)
    return len(matches) > 0
