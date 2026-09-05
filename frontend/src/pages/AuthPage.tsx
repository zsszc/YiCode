import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { LogIn, UserPlus } from 'lucide-react'

interface AuthPageProps {
  onLogin: (token: string, user: { id: number; username: string }) => void
}

/** 解析响应；后端未启动或返回非 JSON 时给出可读错误 */
async function parseJson(resp: Response): Promise<any> {
  const text = await resp.text()
  if (!text) {
    throw new Error(
      resp.ok
        ? '服务器返回了空响应'
        : `无法连接后端服务（HTTP ${resp.status}）。请先启动后端：运行项目根目录的「启动后端.bat」`,
    )
  }
  try {
    return JSON.parse(text)
  } catch {
    throw new Error(`服务器响应异常（HTTP ${resp.status}）：${text.slice(0, 120)}`)
  }
}

export default function AuthPage({ onLogin }: AuthPageProps) {
  const [isRegister, setIsRegister] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')

  const loginMutation = useMutation({
    mutationFn: async () => {
      let resp: Response
      try {
        resp = await fetch('/api/v1/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, password }),
        })
      } catch {
        throw new Error('网络请求失败，请确认后端服务已启动（运行「启动后端.bat」）')
      }
      const data = await parseJson(resp)
      if (!resp.ok) throw new Error(data.detail || '登录失败')
      return data
    },
    onSuccess: (data) => {
      localStorage.setItem('yicode_token', data.access_token)
      onLogin(data.access_token, data.user)
    },
    onError: (err: Error) => setError(err.message),
  })

  const registerMutation = useMutation({
    mutationFn: async () => {
      let resp: Response
      try {
        resp = await fetch('/api/v1/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, password, email: email || undefined }),
        })
      } catch {
        throw new Error('网络请求失败，请确认后端服务已启动（运行「启动后端.bat」）')
      }
      const data = await parseJson(resp)
      if (!resp.ok) throw new Error(data.detail || '注册失败')
      return data
    },
    onSuccess: () => {
      setIsRegister(false)
      setError('')
    },
    onError: (err: Error) => setError(err.message),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (isRegister) {
      registerMutation.mutate()
    } else {
      loginMutation.mutate()
    }
  }

  return (
    <div className="mx-auto max-w-sm py-12">
      <div className="rounded-xl border border-line bg-surface p-6 shadow-card">
        <div className="mb-6 text-center">
          <div className="text-3xl mb-2">🐇</div>
          <h1 className="text-xl font-hand font-bold text-journal-ink">
            {isRegister ? '注册忆码' : '登录忆码'}
          </h1>
          <p className="text-sm text-journal-muted mt-1">
            {isRegister ? '创建你的刷题账号' : '继续你的学习之旅'}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-journal-ink mb-1">用户名</label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              className="w-full rounded-lg border border-line bg-journal-bg px-3 py-2 text-sm text-journal-ink focus:border-brand focus:outline-none"
              placeholder="输入用户名"
              required
              minLength={2}
            />
          </div>

          {isRegister && (
            <div>
              <label className="block text-sm font-medium text-journal-ink mb-1">邮箱（可选）</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="w-full rounded-lg border border-line bg-journal-bg px-3 py-2 text-sm text-journal-ink focus:border-brand focus:outline-none"
                placeholder="your@email.com"
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-journal-ink mb-1">密码</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full rounded-lg border border-line bg-journal-bg px-3 py-2 text-sm text-journal-ink focus:border-brand focus:outline-none"
              placeholder={isRegister ? '至少6位密码' : '输入密码'}
              required
              minLength={6}
            />
          </div>

          {error && (
            <div className="rounded-lg border border-hard/30 bg-hard/10 px-3 py-2 text-sm text-hard">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loginMutation.isPending || registerMutation.isPending}
            className="w-full rounded-lg bg-journal-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-journal-accent/90 disabled:opacity-50"
          >
            {isRegister ? (
              <span className="flex items-center justify-center gap-1">
                <UserPlus size={16} /> 注册
              </span>
            ) : (
              <span className="flex items-center justify-center gap-1">
                <LogIn size={16} /> 登录
              </span>
            )}
          </button>
        </form>

        <div className="mt-4 text-center">
          <button
            onClick={() => { setIsRegister(!isRegister); setError('') }}
            className="text-sm text-journal-accent hover:underline"
          >
            {isRegister ? '已有账号？去登录' : '没有账号？去注册'}
          </button>
        </div>
      </div>
    </div>
  )
}
