import { useEffect, useState } from 'react'
import { getTranscription, startTranscribe, updateTranscription, type Transcription } from '../api'

interface Props {
  recordingId: string
  filename: string
}

export default function TranscriptionView({ recordingId, filename }: Props) {
  const [transcription, setTranscription] = useState<Transcription | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(false)
  const [editText, setEditText] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadTranscription()
  }, [recordingId])

  const loadTranscription = async () => {
    try {
      const t = await getTranscription(recordingId)
      setTranscription(t)
      if (t.status === 'done' && t.text) setEditText(t.text)
    } catch {
      setTranscription(null)
    }
    setLoading(false)
  }

  const handleStart = async () => {
    setError('')
    setLoading(true)
    try {
      const t = await startTranscribe(recordingId)
      setTranscription(t)
      // Poll until done
      if (t.status === 'processing') {
        await pollTranscription()
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '转写失败')
    }
    setLoading(false)
  }

  const pollTranscription = async () => {
    for (let i = 0; i < 60; i++) {
      await new Promise(r => setTimeout(r, 2000))
      try {
        const t = await getTranscription(recordingId)
        setTranscription(t)
        if (t.status === 'done') {
          if (t.text) setEditText(t.text)
          return
        }
        if (t.status === 'error') {
          setError(t.error_message || '转写失败')
          return
        }
      } catch { break }
    }
    setError('转写超时')
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const t = await updateTranscription(recordingId, editText)
      setTranscription(t)
      setEditing(false)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '保存失败')
    }
    setSaving(false)
  }

  if (loading) return <p className="text-gray-400 text-center py-8">加载中...</p>

  if (!transcription || transcription.status === 'pending') {
    return (
      <div className="bg-white rounded-lg shadow p-6 space-y-4 text-center">
        <h2 className="text-lg font-semibold">{filename}</h2>
        <p className="text-gray-400">尚未转写</p>
        {error && <p className="text-red-500 text-sm">{error}</p>}
        <button
          onClick={handleStart}
          className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700"
        >
          开始转写
        </button>
      </div>
    )
  }

  if (transcription.status === 'processing') {
    return (
      <div className="bg-white rounded-lg shadow p-6 text-center space-y-2">
        <h2 className="text-lg font-semibold">{filename}</h2>
        <p className="text-gray-400 animate-pulse">转写中...</p>
      </div>
    )
  }

  if (transcription.status === 'error') {
    return (
      <div className="bg-white rounded-lg shadow p-6 space-y-4 text-center">
        <h2 className="text-lg font-semibold">{filename}</h2>
        <p className="text-red-500">{transcription.error_message || '转写失败'}</p>
        <button onClick={handleStart} className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700">
          重试
        </button>
      </div>
    )
  }

  // status === done
  return (
    <div className="bg-white rounded-lg shadow p-6 space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">{filename}</h2>
        <div className="flex gap-2">
          {!editing ? (
            <button
              onClick={() => { setEditing(true); setEditText(transcription.text || '') }}
              className="text-blue-600 hover:underline text-sm"
            >
              编辑文本
            </button>
          ) : (
            <>
              <button
                onClick={() => setEditing(false)}
                className="text-gray-400 hover:underline text-sm"
              >
                取消
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="text-blue-600 hover:underline text-sm disabled:opacity-50"
              >
                {saving ? '保存中...' : '保存'}
              </button>
            </>
          )}
        </div>
      </div>

      {editing ? (
        <textarea
          value={editText}
          onChange={e => setEditText(e.target.value)}
          className="w-full h-64 border rounded p-3 font-mono text-sm"
        />
      ) : (
        <div className="whitespace-pre-wrap text-sm leading-relaxed max-h-96 overflow-y-auto space-y-2">
          {(transcription.text || '').split('\n\n').map((para, i) => {
            const match = para.match(/^\[说话人 (\S+)\]\s*(.*)/s)
            if (match) {
              const speaker = match[1]
              const text = match[2]
              const isInterviewer = /面试官|interviewer/i.test(speaker)
              return (
                <div key={i} className="flex gap-3 items-start">
                  <span className={`shrink-0 px-2 py-0.5 rounded text-xs font-medium ${isInterviewer ? 'bg-blue-100 text-blue-700' : 'bg-green-100 text-green-700'}`}>
                    {speaker}
                  </span>
                  <p className="text-gray-700">{text}</p>
                </div>
              )
            }
            return <p key={i} className="text-gray-500">{para}</p>
          })}
        </div>
      )}

      {error && <p className="text-red-500 text-sm">{error}</p>}
    </div>
  )
}
