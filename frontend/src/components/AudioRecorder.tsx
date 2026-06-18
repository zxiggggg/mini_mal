import { useRef, useState } from 'react'
import { saveRecording } from '../api'

interface Props {
  onRecorded: () => void
}

const SOURCE_LABELS: Record<string, string> = {
  video_call: '视频会议录制',
  direct_recording: '手机/电脑直接录音',
}

export default function AudioRecorder({ onRecorded }: Props) {
  const [sourceType, setSourceType] = useState('video_call')
  const [recording, setRecording] = useState(false)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [blob, setBlob] = useState<Blob | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const mediaRecorder = useRef<MediaRecorder | null>(null)
  const chunks = useRef<Blob[]>([])

  const start = async () => {
    setError('')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mr = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      mediaRecorder.current = mr
      chunks.current = []

      mr.ondataavailable = (e) => { if (e.data.size > 0) chunks.current.push(e.data) }
      mr.onstop = () => {
        const b = new Blob(chunks.current, { type: 'audio/webm' })
        setBlob(b)
        setAudioUrl(URL.createObjectURL(b))
        stream.getTracks().forEach(t => t.stop())
      }
      mr.start()
      setRecording(true)
      setAudioUrl(null)
      setBlob(null)
    } catch {
      setError('无法访问麦克风')
    }
  }

  const stop = () => {
    mediaRecorder.current?.stop()
    setRecording(false)
  }

  const handleSave = async () => {
    if (!blob) return
    setSaving(true)
    setError('')
    try {
      await saveRecording(blob, sourceType)
      setAudioUrl(null)
      setBlob(null)
      onRecorded()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="bg-white rounded-lg shadow p-6 space-y-4">
      <h2 className="text-lg font-semibold">浏览器录音</h2>
      <div>
        <label className="block text-sm font-medium mb-1">录音来源</label>
        <select
          value={sourceType}
          onChange={e => setSourceType(e.target.value)}
          className="w-full border rounded px-3 py-2"
        >
          {Object.entries(SOURCE_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
      </div>

      <div className="flex gap-2">
        {!recording ? (
          <button onClick={start} className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700">
            开始录音
          </button>
        ) : (
          <button onClick={stop} className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700">
            停止录音
          </button>
        )}
      </div>

      {audioUrl && (
        <div className="space-y-2">
          <p className="text-sm text-gray-500">预览：</p>
          <audio controls src={audioUrl} className="w-full" />
          <button
            onClick={handleSave}
            disabled={saving}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? '保存中...' : '保存录音'}
          </button>
        </div>
      )}

      {error && <p className="text-red-500 text-sm">{error}</p>}
    </div>
  )
}
