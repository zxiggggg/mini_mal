import { useState } from 'react'
import { deleteRecording, exportUrl, type Recording } from '../api'

interface Props {
  recordings: Recording[]
  loading: boolean
  onTranscribe: (recording: Recording) => void
  onRefresh: () => void
}

const SOURCE_LABELS: Record<string, string> = {
  video_call: '视频会议',
  direct_recording: '直接录音',
}

export default function RecordingList({ recordings, loading, onTranscribe, onRefresh }: Props) {
  const [deleting, setDeleting] = useState<string | null>(null)

  const handleDelete = async (r: Recording) => {
    if (!confirm(`确定删除「${r.filename}」？删除后数据不可恢复。`)) return
    setDeleting(r.id)
    try {
      await deleteRecording(r.id)
      onRefresh()
    } catch { alert('删除失败') }
    setDeleting(null)
  }

  if (loading) return <p className="text-gray-400">加载中...</p>
  if (recordings.length === 0) return <p className="text-gray-400">暂无录音</p>

  return (
    <div className="bg-white rounded-lg shadow p-6 space-y-3">
      <h2 className="text-lg font-semibold">录音列表</h2>
      <ul className="divide-y">
        {recordings.map(r => (
          <li key={r.id} className="py-3 flex justify-between items-center">
            <div>
              <p className="font-medium">{r.filename}</p>
              <p className="text-sm text-gray-400">
                {SOURCE_LABELS[r.source_type] ?? r.source_type} · {new Date(r.created_at).toLocaleString('zh-CN')}
              </p>
            </div>
            <div className="flex gap-2 shrink-0">
              <a
                href={exportUrl(r.id, 'json')}
                className="text-xs text-gray-500 hover:underline"
              >
                JSON
              </a>
              <a
                href={exportUrl(r.id, 'csv')}
                className="text-xs text-gray-500 hover:underline"
              >
                CSV
              </a>
              <a
                href={exportUrl(r.id, 'txt')}
                className="text-xs text-gray-500 hover:underline"
              >
                TXT
              </a>
              <button
                onClick={() => onTranscribe(r)}
                className="text-sm text-blue-600 hover:underline"
              >
                转写
              </button>
              <button
                onClick={() => handleDelete(r)}
                disabled={deleting === r.id}
                className="text-sm text-red-500 hover:underline disabled:opacity-50"
              >
                {deleting === r.id ? '删除中...' : '删除'}
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
