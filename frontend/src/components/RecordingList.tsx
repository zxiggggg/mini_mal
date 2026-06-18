import type { Recording } from '../api'

interface Props {
  recordings: Recording[]
  loading: boolean
  onTranscribe: (recording: Recording) => void
}

const SOURCE_LABELS: Record<string, string> = {
  video_call: '视频会议',
  direct_recording: '直接录音',
}

export default function RecordingList({ recordings, loading, onTranscribe }: Props) {
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
            <button
              onClick={() => onTranscribe(r)}
              className="text-sm text-blue-600 hover:underline shrink-0"
            >
              转写
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
