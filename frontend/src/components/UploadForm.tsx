import { useRef, useState } from 'react'
import { uploadRecording } from '../api'

interface Props {
  onUploaded: () => void
}

const SOURCE_LABELS: Record<string, string> = {
  video_call: '视频会议录制',
  direct_recording: '手机/电脑直接录音',
}

export default function UploadForm({ onUploaded }: Props) {
  const [sourceType, setSourceType] = useState('video_call')
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const file = fileRef.current?.files?.[0]
    if (!file) return
    setUploading(true)
    setError('')
    try {
      await uploadRecording(file, sourceType)
      if (fileRef.current) fileRef.current.value = ''
      onUploaded()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '上传失败')
    } finally {
      setUploading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6 space-y-4">
      <h2 className="text-lg font-semibold">上传录音文件</h2>
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
      <div>
        <label className="block text-sm font-medium mb-1">音频文件</label>
        <input ref={fileRef} type="file" accept="audio/*" className="w-full" />
      </div>
      {error && <p className="text-red-500 text-sm">{error}</p>}
      <button
        type="submit"
        disabled={uploading}
        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
      >
        {uploading ? '上传中...' : '上传'}
      </button>
    </form>
  )
}
