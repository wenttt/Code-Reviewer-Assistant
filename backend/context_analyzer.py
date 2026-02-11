"""
AI Code Reviewer - 上下文分析模块
获取完整文件内容和调用关系分析
"""

import re
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import httpx


class FileType(str, Enum):
    """文件类型"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    GO = "go"
    RUST = "rust"
    CPP = "cpp"
    CSHARP = "csharp"
    RUBY = "ruby"
    PHP = "php"
    UNKNOWN = "unknown"


@dataclass
class FunctionInfo:
    """函数/方法信息"""
    name: str
    file: str
    line_start: int
    line_end: Optional[int] = None
    class_name: Optional[str] = None
    params: List[str] = field(default_factory=list)
    return_type: Optional[str] = None


@dataclass
class ImportInfo:
    """导入信息"""
    module: str
    items: List[str]  # 导入的具体项
    file: str
    line: int


@dataclass 
class CallInfo:
    """调用信息"""
    caller: str  # 调用者
    callee: str  # 被调用者
    file: str
    line: int


@dataclass
class FileContext:
    """文件完整上下文"""
    filename: str
    content: str
    language: FileType
    functions: List[FunctionInfo] = field(default_factory=list)
    imports: List[ImportInfo] = field(default_factory=list)
    related_files: List[str] = field(default_factory=list)


class LanguageDetector:
    """编程语言检测器"""
    
    EXTENSION_MAP = {
        '.py': FileType.PYTHON,
        '.js': FileType.JAVASCRIPT,
        '.jsx': FileType.JAVASCRIPT,
        '.ts': FileType.TYPESCRIPT,
        '.tsx': FileType.TYPESCRIPT,
        '.java': FileType.JAVA,
        '.go': FileType.GO,
        '.rs': FileType.RUST,
        '.cpp': FileType.CPP,
        '.cc': FileType.CPP,
        '.cxx': FileType.CPP,
        '.c': FileType.CPP,
        '.h': FileType.CPP,
        '.hpp': FileType.CPP,
        '.cs': FileType.CSHARP,
        '.rb': FileType.RUBY,
        '.php': FileType.PHP,
    }
    
    @classmethod
    def detect(cls, filename: str) -> FileType:
        """根据文件扩展名检测语言"""
        for ext, lang in cls.EXTENSION_MAP.items():
            if filename.endswith(ext):
                return lang
        return FileType.UNKNOWN


class CodeParser:
    """代码解析器 - 提取函数、类、导入等信息"""
    
    # 各语言的函数定义正则
    FUNCTION_PATTERNS = {
        FileType.PYTHON: [
            re.compile(r'^\s*def\s+(\w+)\s*\((.*?)\)(?:\s*->\s*(\w+))?\s*:', re.MULTILINE),
            re.compile(r'^\s*async\s+def\s+(\w+)\s*\((.*?)\)(?:\s*->\s*(\w+))?\s*:', re.MULTILINE),
        ],
        FileType.JAVASCRIPT: [
            re.compile(r'(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>))', re.MULTILINE),
            re.compile(r'^\s*(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{', re.MULTILINE),
        ],
        FileType.TYPESCRIPT: [
            re.compile(r'(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*(?::\s*\w+)?\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>))', re.MULTILINE),
            re.compile(r'^\s*(?:public|private|protected)?\s*(?:async\s+)?(\w+)\s*\([^)]*\)(?:\s*:\s*\w+)?\s*\{', re.MULTILINE),
        ],
        FileType.JAVA: [
            re.compile(r'(?:public|private|protected)?\s*(?:static)?\s*(?:\w+)\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+\w+)?\s*\{', re.MULTILINE),
        ],
        FileType.GO: [
            re.compile(r'^func\s+(?:\([^)]+\)\s+)?(\w+)\s*\([^)]*\)', re.MULTILINE),
        ],
    }
    
    # 各语言的导入正则
    IMPORT_PATTERNS = {
        FileType.PYTHON: [
            re.compile(r'^import\s+([\w.]+)(?:\s+as\s+\w+)?', re.MULTILINE),
            re.compile(r'^from\s+([\w.]+)\s+import\s+(.+?)(?:\s*#|$)', re.MULTILINE),
        ],
        FileType.JAVASCRIPT: [
            re.compile(r'import\s+(?:(?:\{([^}]+)\}|(\w+))\s+from\s+)?[\'"]([^\'"]+)[\'"]', re.MULTILINE),
            re.compile(r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)', re.MULTILINE),
        ],
        FileType.TYPESCRIPT: [
            re.compile(r'import\s+(?:(?:\{([^}]+)\}|(\w+))\s+from\s+)?[\'"]([^\'"]+)[\'"]', re.MULTILINE),
        ],
        FileType.JAVA: [
            re.compile(r'^import\s+([\w.]+);', re.MULTILINE),
        ],
        FileType.GO: [
            re.compile(r'import\s+(?:"([^"]+)"|\(\s*([^)]+)\s*\))', re.MULTILINE),
        ],
    }
    
    # 类定义正则
    CLASS_PATTERNS = {
        FileType.PYTHON: re.compile(r'^class\s+(\w+)(?:\s*\([^)]*\))?\s*:', re.MULTILINE),
        FileType.JAVASCRIPT: re.compile(r'^class\s+(\w+)(?:\s+extends\s+\w+)?\s*\{', re.MULTILINE),
        FileType.TYPESCRIPT: re.compile(r'^(?:export\s+)?class\s+(\w+)(?:\s+extends\s+\w+)?(?:\s+implements\s+[\w,\s]+)?\s*\{', re.MULTILINE),
        FileType.JAVA: re.compile(r'(?:public|private)?\s*class\s+(\w+)(?:\s+extends\s+\w+)?(?:\s+implements\s+[\w,\s]+)?\s*\{', re.MULTILINE),
    }
    
    @classmethod
    def parse_functions(cls, content: str, language: FileType, filename: str) -> List[FunctionInfo]:
        """解析代码中的函数定义"""
        functions = []
        patterns = cls.FUNCTION_PATTERNS.get(language, [])
        
        for pattern in patterns:
            for match in pattern.finditer(content):
                # 获取函数名 (不同模式可能在不同的组)
                name = None
                for group in match.groups():
                    if group and not group.startswith('('):
                        name = group.strip()
                        break
                
                if name:
                    line_num = content[:match.start()].count('\n') + 1
                    functions.append(FunctionInfo(
                        name=name,
                        file=filename,
                        line_start=line_num
                    ))
        
        return functions
    
    @classmethod
    def parse_imports(cls, content: str, language: FileType, filename: str) -> List[ImportInfo]:
        """解析代码中的导入语句"""
        imports = []
        patterns = cls.IMPORT_PATTERNS.get(language, [])
        
        for pattern in patterns:
            for match in pattern.finditer(content):
                groups = match.groups()
                module = None
                items = []
                
                # 根据不同语言处理匹配组
                if language == FileType.PYTHON:
                    if 'from' in match.group(0):
                        module = groups[0]
                        items = [i.strip() for i in groups[1].split(',')] if groups[1] else []
                    else:
                        module = groups[0]
                elif language in (FileType.JAVASCRIPT, FileType.TYPESCRIPT):
                    module = groups[-1] if groups[-1] else groups[0]
                    if groups[0]:
                        items = [i.strip() for i in groups[0].split(',')]
                elif language == FileType.JAVA:
                    module = groups[0]
                elif language == FileType.GO:
                    module = groups[0] or groups[1]
                
                if module:
                    line_num = content[:match.start()].count('\n') + 1
                    imports.append(ImportInfo(
                        module=module,
                        items=items,
                        file=filename,
                        line=line_num
                    ))
        
        return imports
    
    @classmethod
    def extract_modified_functions(cls, diff: str, language: FileType) -> List[str]:
        """从diff中提取被修改的函数名"""
        modified_functions = []
        patterns = cls.FUNCTION_PATTERNS.get(language, [])
        
        # 只检查新增或修改的行
        lines = diff.split('\n')
        for line in lines:
            if line.startswith('+') and not line.startswith('+++'):
                for pattern in patterns:
                    match = pattern.search(line[1:])  # 去掉+号
                    if match:
                        for group in match.groups():
                            if group and not group.startswith('('):
                                modified_functions.append(group.strip())
                                break
        
        return list(set(modified_functions))


class ContextEnhancer:
    """上下文增强器 - 获取完整文件和相关上下文"""
    
    GITHUB_API_BASE = "https://api.github.com"
    
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    async def get_file_content(
        self, 
        owner: str, 
        repo: str, 
        path: str, 
        ref: str = "main"
    ) -> Optional[str]:
        """获取文件的完整内容"""
        url = f"{self.GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={**self.headers, "Accept": "application/vnd.github.v3.raw"},
                params={"ref": ref},
                timeout=30.0
            )
            
            if response.status_code == 200:
                return response.text
            return None
    
    async def get_full_context(
        self,
        owner: str,
        repo: str,
        files: List[Dict],  # PR中的文件列表
        head_ref: str
    ) -> List[FileContext]:
        """获取PR中所有文件的完整上下文"""
        contexts = []
        
        for file_info in files:
            filename = file_info.get('filename', '')
            status = file_info.get('status', '')
            
            # 删除的文件不需要获取内容
            if status == 'deleted':
                continue
            
            # 获取完整文件内容
            content = await self.get_file_content(owner, repo, filename, head_ref)
            
            if content:
                language = LanguageDetector.detect(filename)
                
                # 解析函数和导入
                functions = CodeParser.parse_functions(content, language, filename)
                imports = CodeParser.parse_imports(content, language, filename)
                
                # 查找相关文件
                related = self._find_related_files(imports, files)
                
                contexts.append(FileContext(
                    filename=filename,
                    content=content,
                    language=language,
                    functions=functions,
                    imports=imports,
                    related_files=related
                ))
        
        return contexts
    
    def _find_related_files(
        self, 
        imports: List[ImportInfo], 
        pr_files: List[Dict]
    ) -> List[str]:
        """根据导入关系查找相关文件"""
        related = []
        pr_filenames = {f.get('filename', '') for f in pr_files}
        
        for imp in imports:
            # 转换导入路径为可能的文件名
            possible_files = self._import_to_filenames(imp.module)
            for pf in possible_files:
                if pf in pr_filenames:
                    related.append(pf)
        
        return list(set(related))
    
    def _import_to_filenames(self, module: str) -> List[str]:
        """将导入模块名转换为可能的文件名"""
        # 替换.为/
        base = module.replace('.', '/')
        
        # 生成可能的文件扩展名
        extensions = ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go']
        
        filenames = []
        for ext in extensions:
            filenames.append(f"{base}{ext}")
            filenames.append(f"{base}/index{ext}")
            filenames.append(f"src/{base}{ext}")
        
        return filenames


def build_context_prompt(contexts: List[FileContext], diff: str) -> str:
    """构建包含完整上下文的Prompt"""
    prompt_parts = []
    
    # 添加文件完整内容
    prompt_parts.append("## 完整文件内容参考\n")
    for ctx in contexts:
        prompt_parts.append(f"### {ctx.filename} ({ctx.language.value})")
        
        # 函数列表
        if ctx.functions:
            func_names = [f.name for f in ctx.functions]
            prompt_parts.append(f"**定义的函数**: {', '.join(func_names)}")
        
        # 导入列表
        if ctx.imports:
            imp_names = [imp.module for imp in ctx.imports]
            prompt_parts.append(f"**导入模块**: {', '.join(imp_names[:10])}")  # 限制数量
        
        # 完整内容（限制长度）
        content = ctx.content
        if len(content) > 5000:
            content = content[:5000] + "\n... (内容截断)"
        prompt_parts.append(f"```{ctx.language.value}")
        prompt_parts.append(content)
        prompt_parts.append("```\n")
    
    # 添加diff
    prompt_parts.append("## 本次PR的代码变更 (Diff)\n")
    prompt_parts.append("```diff")
    prompt_parts.append(diff)
    prompt_parts.append("```")
    
    return "\n".join(prompt_parts)
