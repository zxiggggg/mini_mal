import { useEffect, useState } from 'react'

export default function App() {
  const [status, setStatus] = useState<string>('checking...')

  useEffect(() => {
    fetch('/api/health')
      .then(r => r.json())
      .then(d => setStatus(d.status))
      .catch(() => setStatus('error'))
  }, [])

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center space-y-4">
        <h1 className="text-3xl font-bold">mini_mal</h1>
        <p className="text-gray-500">面试复盘工具</p>
        <p className="text-sm text-gray-400">
          API: <span className={status === 'ok' ? 'text-green-600' : 'text-red-600'}>{status}</span>
        </p>
      </div>
    </div>
  )
}
