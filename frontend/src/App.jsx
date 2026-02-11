import { useState, useEffect } from 'react'

// API配置 - 自动检测环境
const getApiBase = () => {
  const hostname = window.location.hostname
  
  // Sandbox环境
  if (hostname.includes('sandbox')) {
    return 'https://8000-iz5bvpy7ypwi0p95ye53l-3844e1b6.sandbox.novita.ai/api'
  }
  
  // 本地开发环境 - 直接访问后端
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'http://localhost:8000/api'
  }
  
  // 其他情况使用相对路径（通过代理）
  return '/api'
}

const API_BASE = getApiBase()

// 工具函数
const api = {
  async validateToken(token) {
    const res = await fetch(`${API_BASE}/auth/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token })
    })
    return res.json()
  },

  async getRepos(token) {
    const res = await fetch(`${API_BASE}/repos`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!res.ok) throw new Error('获取仓库列表失败')
    return res.json()
  },

  async getPulls(token, owner, repo, state = 'open') {
    const res = await fetch(`${API_BASE}/repos/${owner}/${repo}/pulls?state=${state}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!res.ok) throw new Error('获取PR列表失败')
    return res.json()
  },

  async getPullDetail(token, owner, repo, pullNumber) {
    const res = await fetch(`${API_BASE}/repos/${owner}/${repo}/pulls/${pullNumber}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!res.ok) throw new Error('获取PR详情失败')
    return res.json()
  },

  async analyzePR(token, owner, repo, pullNumber) {
    const res = await fetch(`${API_BASE}/repos/${owner}/${repo}/pulls/${pullNumber}/analyze`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!res.ok) throw new Error('分析PR失败')
    return res.json()
  },

  async performReview(token, owner, repo, pullNumber, config) {
    const res = await fetch(`${API_BASE}/review`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        owner,
        repo,
        pull_number: pullNumber,
        openai_api_key: config.openaiKey,
        openai_base_url: config.openaiBaseUrl || null,
        enable_security_filter: config.enableSecurityFilter,
        enable_context_enhancement: config.enableContextEnhancement,
        model: config.model,
        provider: config.provider,
        ollama_base_url: config.ollamaBaseUrl || null
      })
    })
    return res.json()
  },

  async getProviders() {
    const res = await fetch(`${API_BASE}/models/providers`)
    return res.json()
  }
}

// ================== 组件 ==================

// 配置面板组件
function ConfigPanel({ config, setConfig, onValidate, isValidating, user }) {
  const [showAdvanced, setShowAdvanced] = useState(false)

  return (
    <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
      <h2 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
        <span className="text-2xl">🔐</span> 配置
      </h2>

      {/* GitHub Token */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          GitHub Personal Access Token
        </label>
        <input
          type="password"
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
          placeholder="ghp_xxxxxxxxxxxx"
          value={config.githubToken}
          onChange={e => setConfig({ ...config, githubToken: e.target.value })}
        />
        <p className="text-xs text-gray-500 mt-1">
          需要 <code className="bg-gray-100 px-1 rounded">repo</code> 权限
        </p>
      </div>

      {/* 模型提供商选择 */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          AI模型提供商
        </label>
        <div className="grid grid-cols-3 gap-2">
          <button
            onClick={() => setConfig({ ...config, provider: 'deepseek', model: 'deepseek-chat' })}
            className={`p-3 rounded-lg border-2 transition text-left ${
              config.provider === 'deepseek' 
                ? 'border-purple-500 bg-purple-50' 
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <div className="font-medium">🚀 DeepSeek</div>
            <div className="text-xs text-gray-500">高性价比</div>
          </button>
          <button
            onClick={() => setConfig({ ...config, provider: 'openai', model: 'gpt-4o' })}
            className={`p-3 rounded-lg border-2 transition text-left ${
              config.provider === 'openai' 
                ? 'border-blue-500 bg-blue-50' 
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <div className="font-medium">☁️ OpenAI</div>
            <div className="text-xs text-gray-500">云端API</div>
          </button>
          <button
            onClick={() => setConfig({ ...config, provider: 'ollama', model: 'codellama' })}
            className={`p-3 rounded-lg border-2 transition text-left ${
              config.provider === 'ollama' 
                ? 'border-green-500 bg-green-50' 
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <div className="font-medium">🏠 Ollama</div>
            <div className="text-xs text-gray-500">本地模型</div>
          </button>
        </div>
      </div>

      {/* DeepSeek配置 */}
      {config.provider === 'deepseek' && (
        <>
          <div className="mb-4 p-3 bg-purple-50 rounded-lg">
            <p className="text-sm text-purple-800">
              🚀 <strong>DeepSeek</strong>: 代码能力强，价格实惠，推荐使用
            </p>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              DeepSeek API Key
            </label>
            <input
              type="password"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition"
              placeholder="sk-xxxxxxxxxxxx"
              value={config.openaiKey}
              onChange={e => setConfig({ ...config, openaiKey: e.target.value })}
            />
            <p className="text-xs text-gray-500 mt-1">
              从 <a href="https://platform.deepseek.com/api_keys" target="_blank" className="text-purple-600 hover:underline">platform.deepseek.com</a> 获取
            </p>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              模型选择
            </label>
            <select
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
              value={config.model}
              onChange={e => setConfig({ ...config, model: e.target.value })}
            >
              <option value="deepseek-chat">DeepSeek Chat (推荐)</option>
              <option value="deepseek-coder">DeepSeek Coder</option>
            </select>
          </div>
        </>
      )}

      {/* OpenAI配置 */}
      {config.provider === 'openai' && (
        <>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              OpenAI API Key
            </label>
            <input
              type="password"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
              placeholder="sk-xxxxxxxxxxxx"
              value={config.openaiKey}
              onChange={e => setConfig({ ...config, openaiKey: e.target.value })}
            />
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              模型选择
            </label>
            <select
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              value={config.model}
              onChange={e => setConfig({ ...config, model: e.target.value })}
            >
              <option value="gpt-4o">GPT-4o (推荐)</option>
              <option value="gpt-4-turbo">GPT-4 Turbo</option>
              <option value="gpt-3.5-turbo">GPT-3.5 Turbo (经济)</option>
            </select>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              API Base URL <span className="text-gray-400">(可选)</span>
            </label>
            <input
              type="text"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
              placeholder="https://api.openai.com/v1"
              value={config.openaiBaseUrl}
              onChange={e => setConfig({ ...config, openaiBaseUrl: e.target.value })}
            />
          </div>
        </>
      )}

      {/* Ollama配置 */}
      {config.provider === 'ollama' && (
        <>
          <div className="mb-4 p-3 bg-green-50 rounded-lg">
            <p className="text-sm text-green-800">
              🔒 <strong>本地模式</strong>: 代码数据不会发送到外部服务器
            </p>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Ollama 服务地址
            </label>
            <input
              type="text"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 transition"
              placeholder="http://localhost:11434"
              value={config.ollamaBaseUrl}
              onChange={e => setConfig({ ...config, ollamaBaseUrl: e.target.value })}
            />
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              模型选择
            </label>
            <select
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
              value={config.model}
              onChange={e => setConfig({ ...config, model: e.target.value })}
            >
              <option value="codellama">CodeLlama (代码专用)</option>
              <option value="deepseek-coder">DeepSeek Coder</option>
              <option value="llama3">Llama 3</option>
              <option value="mistral">Mistral</option>
            </select>
          </div>
        </>
      )}

      {/* 高级选项 */}
      <div className="mb-4">
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
        >
          {showAdvanced ? '▼' : '▶'} 高级选项
        </button>
        
        {showAdvanced && (
          <div className="mt-3 p-4 bg-gray-50 rounded-lg space-y-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={config.enableSecurityFilter}
                onChange={e => setConfig({ ...config, enableSecurityFilter: e.target.checked })}
                className="rounded text-blue-600"
              />
              <span className="text-sm">🔒 启用敏感信息过滤</span>
            </label>
            <p className="text-xs text-gray-500 ml-6">自动检测并脱敏API Key、密码等敏感信息</p>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={config.enableContextEnhancement}
                onChange={e => setConfig({ ...config, enableContextEnhancement: e.target.checked })}
                className="rounded text-blue-600"
              />
              <span className="text-sm">📖 启用上下文增强</span>
            </label>
            <p className="text-xs text-gray-500 ml-6">获取完整文件内容，提供更准确的审查</p>
          </div>
        )}
      </div>

      {/* 验证按钮 */}
      <button
        onClick={onValidate}
        disabled={!config.githubToken || isValidating}
        className="w-full py-2 px-4 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition flex items-center justify-center gap-2"
      >
        {isValidating ? (
          <>
            <span className="animate-spin">⏳</span> 验证中...
          </>
        ) : (
          <>验证连接</>
        )}
      </button>

      {/* 用户信息 */}
      {user && (
        <div className="mt-4 p-4 bg-green-50 rounded-lg flex items-center gap-3">
          <img src={user.avatar_url} alt={user.login} className="w-10 h-10 rounded-full" />
          <div>
            <p className="font-medium text-green-800">{user.name || user.login}</p>
            <p className="text-sm text-green-600">@{user.login}</p>
          </div>
          <span className="ml-auto text-green-600 text-xl">✓</span>
        </div>
      )}
    </div>
  )
}

// 仓库列表组件
function RepoList({ repos, selectedRepo, onSelect, loading }) {
  const [search, setSearch] = useState('')

  const filteredRepos = repos.filter(repo =>
    repo.full_name.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
      <h2 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
        <span className="text-2xl">📁</span> 选择仓库
      </h2>

      {loading ? (
        <div className="text-center py-8 text-gray-500">
          <span className="animate-spin inline-block text-2xl mb-2">⏳</span>
          <p>加载仓库列表...</p>
        </div>
      ) : (
        <>
          <input
            type="text"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg mb-4 focus:ring-2 focus:ring-blue-500"
            placeholder="🔍 搜索仓库..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />

          <div className="max-h-64 overflow-y-auto space-y-2">
            {filteredRepos.map(repo => (
              <div
                key={repo.full_name}
                onClick={() => onSelect(repo)}
                className={`p-3 rounded-lg cursor-pointer transition ${
                  selectedRepo?.full_name === repo.full_name
                    ? 'bg-blue-100 border-2 border-blue-500'
                    : 'bg-gray-50 hover:bg-gray-100 border-2 border-transparent'
                }`}
              >
                <div className="flex items-center gap-2">
                  <span>{repo.private ? '🔒' : '📂'}</span>
                  <span className="font-medium">{repo.full_name}</span>
                </div>
                {repo.description && (
                  <p className="text-sm text-gray-500 mt-1 truncate">{repo.description}</p>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

// PR列表组件
function PRList({ pulls, selectedPR, onSelect, loading, repoName }) {
  return (
    <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
      <h2 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
        <span className="text-2xl">🔀</span> Pull Requests
        {repoName && <span className="text-sm font-normal text-gray-500">({repoName})</span>}
      </h2>

      {loading ? (
        <div className="text-center py-8 text-gray-500">
          <span className="animate-spin inline-block text-2xl mb-2">⏳</span>
          <p>加载PR列表...</p>
        </div>
      ) : pulls.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <span className="text-4xl mb-2">📭</span>
          <p>暂无Open状态的PR</p>
        </div>
      ) : (
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {pulls.map(pr => (
            <div
              key={pr.number}
              onClick={() => onSelect(pr)}
              className={`p-4 rounded-lg cursor-pointer transition ${
                selectedPR?.number === pr.number
                  ? 'bg-blue-100 border-2 border-blue-500'
                  : 'bg-gray-50 hover:bg-gray-100 border-2 border-transparent'
              }`}
            >
              <div className="flex items-start gap-3">
                <img src={pr.author_avatar} alt={pr.author} className="w-8 h-8 rounded-full" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-green-600 font-mono">#{pr.number}</span>
                    <span className="font-medium truncate">{pr.title}</span>
                  </div>
                  <p className="text-sm text-gray-500 mt-1">
                    {pr.head_ref} → {pr.base_ref} · by {pr.author}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// PR分析预览组件
function PRAnalysis({ analysis, loading }) {
  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
        <div className="text-center py-4 text-gray-500">
          <span className="animate-spin inline-block text-2xl mb-2">⏳</span>
          <p>分析PR中...</p>
        </div>
      </div>
    )
  }

  if (!analysis) return null

  return (
    <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
      <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
        <span>📊</span> PR分析预览
      </h3>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <div className="bg-blue-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-blue-600">{analysis.total_files}</p>
          <p className="text-xs text-gray-600">总文件数</p>
        </div>
        <div className="bg-green-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-green-600">{analysis.reviewable_files}</p>
          <p className="text-xs text-gray-600">待审查</p>
        </div>
        <div className="bg-yellow-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-yellow-600">{analysis.chunks_needed}</p>
          <p className="text-xs text-gray-600">审查分片</p>
        </div>
        <div className="bg-purple-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-purple-600">{analysis.estimated_time}</p>
          <p className="text-xs text-gray-600">预计时间</p>
        </div>
      </div>

      {/* 文件分组 */}
      {Object.keys(analysis.file_groups).length > 0 && (
        <div className="mt-4">
          <p className="text-sm font-medium text-gray-700 mb-2">文件分组:</p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(analysis.file_groups).map(([name, group]) => (
              <span 
                key={name}
                className={`px-3 py-1 rounded-full text-xs font-medium ${
                  group.priority === 'critical' ? 'bg-red-100 text-red-800' :
                  group.priority === 'high' ? 'bg-orange-100 text-orange-800' :
                  group.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-gray-100 text-gray-800'
                }`}
              >
                {name}: {group.count}个文件
              </span>
            ))}
          </div>
        </div>
      )}

      {/* 跳过的文件 */}
      {analysis.skipped_files?.length > 0 && (
        <div className="mt-4">
          <p className="text-sm text-gray-600">
            ⏭️ 将跳过 {analysis.skipped_files.length} 个文件（lock文件、构建产物等）
          </p>
        </div>
      )}
    </div>
  )
}

// 审查结果组件
function ReviewResult({ review, pr, meta }) {
  const severityConfig = {
    critical: { color: 'bg-red-100 text-red-800 border-red-300', icon: '🔴', label: '严重' },
    major: { color: 'bg-orange-100 text-orange-800 border-orange-300', icon: '🟠', label: '重要' },
    minor: { color: 'bg-yellow-100 text-yellow-800 border-yellow-300', icon: '🟡', label: '轻微' },
    info: { color: 'bg-blue-100 text-blue-800 border-blue-300', icon: '🔵', label: '提示' }
  }

  const categoryLabels = {
    bug: '潜在Bug',
    security: '安全问题',
    performance: '性能问题',
    style: '代码风格',
    maintainability: '可维护性',
    best_practice: '最佳实践'
  }

  const getScoreColor = (score) => {
    if (score >= 90) return 'text-green-600'
    if (score >= 80) return 'text-blue-600'
    if (score >= 70) return 'text-yellow-600'
    if (score >= 60) return 'text-orange-600'
    return 'text-red-600'
  }

  return (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <h2 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
        <span className="text-2xl">📋</span> 审查报告
        <span className="text-sm font-normal text-gray-500">
          PR #{pr.number}: {pr.title}
        </span>
      </h2>

      {/* 审查元信息 */}
      {meta && (
        <div className="flex flex-wrap gap-2 mb-4">
          {meta.chunks_count > 1 && (
            <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded text-xs">
              📦 {meta.chunks_count}个分片
            </span>
          )}
          {meta.context_enhanced && (
            <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
              📖 上下文增强
            </span>
          )}
          {meta.security_filtered && (
            <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs">
              🔒 已过滤敏感信息
            </span>
          )}
          {meta.skipped_files_count > 0 && (
            <span className="px-2 py-1 bg-gray-100 text-gray-800 rounded text-xs">
              ⏭️ 跳过{meta.skipped_files_count}个文件
            </span>
          )}
        </div>
      )}

      {/* 评分卡片 */}
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl p-6 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-gray-600 mb-1">综合评分</p>
            <p className={`text-5xl font-bold ${getScoreColor(review.score)}`}>
              {review.score}
              <span className="text-2xl text-gray-400">/100</span>
            </p>
          </div>
          <div className="text-6xl">
            {review.score >= 90 ? '🏆' : review.score >= 80 ? '👍' : review.score >= 70 ? '🤔' : '⚠️'}
          </div>
        </div>
        <p className="mt-4 text-gray-700">{review.summary}</p>
      </div>

      {/* 敏感信息警告 */}
      {review.filtered_secrets_count > 0 && (
        <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <p className="text-amber-800 flex items-center gap-2">
            <span>🔐</span>
            <span>检测到 <strong>{review.filtered_secrets_count}</strong> 处敏感信息已被自动脱敏处理</span>
          </p>
        </div>
      )}

      {/* 问题列表 */}
      {review.issues && review.issues.length > 0 && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-3 flex items-center gap-2">
            <span>⚠️</span> 发现的问题 ({review.issues.length})
          </h3>
          <div className="space-y-3">
            {review.issues.map((issue, idx) => {
              const config = severityConfig[issue.severity] || severityConfig.info
              return (
                <div key={idx} className={`p-4 rounded-lg border ${config.color}`}>
                  <div className="flex items-center gap-2 mb-2">
                    <span>{config.icon}</span>
                    <span className="font-medium">{config.label}</span>
                    <span className="text-xs px-2 py-0.5 bg-white/50 rounded">
                      {categoryLabels[issue.category] || issue.category}
                    </span>
                    <span className="text-xs text-gray-600 ml-auto">
                      📄 {issue.file} {issue.line && `(L${issue.line})`}
                    </span>
                  </div>
                  <p className="text-sm">{issue.description}</p>
                  {issue.suggestion && (
                    <p className="text-sm mt-2 pt-2 border-t border-current/20">
                      💡 <strong>建议:</strong> {issue.suggestion}
                    </p>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* 代码亮点 */}
      {review.highlights && review.highlights.length > 0 && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-3 flex items-center gap-2">
            <span>✨</span> 代码亮点
          </h3>
          <ul className="space-y-2">
            {review.highlights.map((highlight, idx) => (
              <li key={idx} className="flex items-start gap-2 text-gray-700">
                <span className="text-green-500">✓</span>
                <span>{highlight}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 改进建议 */}
      {review.suggestions && review.suggestions.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-gray-800 mb-3 flex items-center gap-2">
            <span>💡</span> 改进建议
          </h3>
          <ul className="space-y-2">
            {review.suggestions.map((suggestion, idx) => (
              <li key={idx} className="flex items-start gap-2 text-gray-700">
                <span className="text-blue-500">→</span>
                <span>{suggestion}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

// ================== 主应用 ==================

function App() {
  // 状态
  const [config, setConfig] = useState({
    githubToken: '',
    openaiKey: '',
    openaiBaseUrl: '',
    provider: 'deepseek',  // 默认使用DeepSeek
    model: 'deepseek-chat',
    ollamaBaseUrl: 'http://localhost:11434',
    enableSecurityFilter: true,
    enableContextEnhancement: true
  })
  const [user, setUser] = useState(null)
  const [repos, setRepos] = useState([])
  const [selectedRepo, setSelectedRepo] = useState(null)
  const [pulls, setPulls] = useState([])
  const [selectedPR, setSelectedPR] = useState(null)
  const [prAnalysis, setPRAnalysis] = useState(null)
  const [review, setReview] = useState(null)
  const [reviewMeta, setReviewMeta] = useState(null)

  // 加载状态
  const [isValidating, setIsValidating] = useState(false)
  const [loadingRepos, setLoadingRepos] = useState(false)
  const [loadingPulls, setLoadingPulls] = useState(false)
  const [loadingAnalysis, setLoadingAnalysis] = useState(false)
  const [isReviewing, setIsReviewing] = useState(false)
  const [error, setError] = useState(null)

  // 验证Token
  const handleValidate = async () => {
    setIsValidating(true)
    setError(null)
    try {
      const result = await api.validateToken(config.githubToken)
      if (result.valid) {
        setUser(result.user)
        setLoadingRepos(true)
        const reposResult = await api.getRepos(config.githubToken)
        setRepos(reposResult.repos)
      } else {
        setError(result.error || 'Token验证失败')
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setIsValidating(false)
      setLoadingRepos(false)
    }
  }

  // 选择仓库
  const handleSelectRepo = async (repo) => {
    setSelectedRepo(repo)
    setSelectedPR(null)
    setReview(null)
    setReviewMeta(null)
    setPRAnalysis(null)
    setPulls([])
    setLoadingPulls(true)
    setError(null)

    try {
      const [owner, repoName] = repo.full_name.split('/')
      const result = await api.getPulls(config.githubToken, owner, repoName)
      setPulls(result.pulls)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoadingPulls(false)
    }
  }

  // 选择PR
  const handleSelectPR = async (pr) => {
    setSelectedPR(pr)
    setReview(null)
    setReviewMeta(null)
    setPRAnalysis(null)
    setLoadingAnalysis(true)

    try {
      const [owner, repoName] = selectedRepo.full_name.split('/')
      const analysis = await api.analyzePR(config.githubToken, owner, repoName, pr.number)
      setPRAnalysis(analysis)
    } catch (e) {
      console.error('分析PR失败:', e)
    } finally {
      setLoadingAnalysis(false)
    }
  }

  // 执行审查
  const handleReview = async () => {
    if (!selectedRepo || !selectedPR) {
      setError('请先选择PR')
      return
    }

    if ((config.provider === 'openai' || config.provider === 'deepseek') && !config.openaiKey) {
      setError(`请配置${config.provider === 'deepseek' ? 'DeepSeek' : 'OpenAI'} API Key`)
      return
    }

    setIsReviewing(true)
    setError(null)
    setReview(null)
    setReviewMeta(null)

    try {
      const [owner, repoName] = selectedRepo.full_name.split('/')
      const result = await api.performReview(
        config.githubToken,
        owner,
        repoName,
        selectedPR.number,
        config
      )

      if (result.success) {
        setReview(result.review)
        setReviewMeta(result.meta)
      } else {
        setError(result.error || '审查失败')
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setIsReviewing(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-3xl">🤖</span>
              <div>
                <h1 className="text-xl font-bold text-gray-800">AI Code Reviewer</h1>
                <p className="text-sm text-gray-500">智能代码审查助手 v2.0</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              {config.provider === 'ollama' && (
                <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs">
                  🏠 本地模式
                </span>
              )}
              {user && (
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <img src={user.avatar_url} alt={user.login} className="w-6 h-6 rounded-full" />
                  <span>{user.login}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        {/* Error Alert */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 flex items-center gap-2">
            <span>❌</span>
            <span>{error}</span>
            <button onClick={() => setError(null)} className="ml-auto hover:text-red-900">✕</button>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 左侧面板 */}
          <div className="lg:col-span-1">
            <ConfigPanel
              config={config}
              setConfig={setConfig}
              onValidate={handleValidate}
              isValidating={isValidating}
              user={user}
            />

            {user && (
              <RepoList
                repos={repos}
                selectedRepo={selectedRepo}
                onSelect={handleSelectRepo}
                loading={loadingRepos}
              />
            )}
          </div>

          {/* 右侧面板 */}
          <div className="lg:col-span-2">
            {selectedRepo && (
              <PRList
                pulls={pulls}
                selectedPR={selectedPR}
                onSelect={handleSelectPR}
                loading={loadingPulls}
                repoName={selectedRepo.full_name}
              />
            )}

            {/* PR分析预览 */}
            {selectedPR && (
              <PRAnalysis analysis={prAnalysis} loading={loadingAnalysis} />
            )}

            {/* 审查按钮 */}
            {selectedPR && (
              <div className="mb-6">
                <button
                  onClick={handleReview}
                  disabled={isReviewing || ((config.provider === 'openai' || config.provider === 'deepseek') && !config.openaiKey)}
                  className="w-full py-4 px-6 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-xl font-bold text-lg hover:from-purple-700 hover:to-blue-700 disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed transition-all shadow-lg hover:shadow-xl flex items-center justify-center gap-3"
                >
                  {isReviewing ? (
                    <>
                      <span className="animate-spin text-2xl">⏳</span>
                      <span>AI正在审查代码...</span>
                    </>
                  ) : (
                    <>
                      <span className="text-2xl">🚀</span>
                      <span>开始AI代码审查</span>
                    </>
                  )}
                </button>
                {(config.provider === 'openai' || config.provider === 'deepseek') && !config.openaiKey && (
                  <p className="text-center text-sm text-orange-600 mt-2">
                    ⚠️ 请先配置{config.provider === 'deepseek' ? 'DeepSeek' : 'OpenAI'} API Key
                  </p>
                )}
              </div>
            )}

            {/* 审查结果 */}
            {review && <ReviewResult review={review} pr={selectedPR} meta={reviewMeta} />}

            {/* 空状态 */}
            {!selectedRepo && user && (
              <div className="bg-white rounded-xl shadow-lg p-12 text-center">
                <span className="text-6xl mb-4 inline-block">👈</span>
                <p className="text-xl text-gray-600">请从左侧选择一个仓库</p>
              </div>
            )}

            {!user && (
              <div className="bg-white rounded-xl shadow-lg p-12 text-center">
                <span className="text-6xl mb-4 inline-block">🔑</span>
                <h2 className="text-2xl font-bold text-gray-800 mb-4">欢迎使用 AI Code Reviewer v2.0</h2>
                <p className="text-gray-600 mb-6">
                  请在左侧配置面板输入您的GitHub Token来开始使用
                </p>
                
                {/* 新功能介绍 */}
                <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-4 text-left mb-6">
                  <p className="font-medium text-gray-700 mb-3">✨ v2.0 新功能:</p>
                  <ul className="text-sm text-gray-600 space-y-2">
                    <li className="flex items-center gap-2">
                      <span className="text-green-500">✓</span>
                      🔒 敏感信息自动检测和脱敏
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="text-green-500">✓</span>
                      📦 大PR智能分片审查
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="text-green-500">✓</span>
                      📖 完整文件上下文增强
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="text-green-500">✓</span>
                      🏠 支持Ollama本地模型
                    </li>
                  </ul>
                </div>

                <div className="bg-gray-50 rounded-lg p-4 text-left text-sm">
                  <p className="font-medium text-gray-700 mb-2">如何获取GitHub Token:</p>
                  <ol className="list-decimal list-inside text-gray-600 space-y-1">
                    <li>打开 GitHub Settings → Developer settings</li>
                    <li>点击 Personal access tokens → Tokens (classic)</li>
                    <li>点击 Generate new token</li>
                    <li>勾选 <code className="bg-gray-200 px-1 rounded">repo</code> 权限</li>
                    <li>生成并复制Token</li>
                  </ol>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 mt-12 py-6">
        <div className="max-w-6xl mx-auto px-4 text-center text-gray-500 text-sm">
          <p>AI Code Reviewer v2.0.0 - Powered by OpenAI / Ollama & GitHub API</p>
          <p className="mt-1 text-xs">
            🔒 敏感信息过滤 | 📦 智能分片 | 📖 上下文增强 | 🏠 本地模型支持
          </p>
        </div>
      </footer>
    </div>
  )
}

export default App
