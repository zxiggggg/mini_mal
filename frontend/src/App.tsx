import { useCallback, useEffect, useState } from 'react'
import { fetchRecordings, type Recording } from './api'
import AudioRecorder from './components/AudioRecorder'
import RecordingList from './components/RecordingList'
import UploadForm from './components/UploadForm'

export default function App() {
  const [recordings, setRecordings] = useState<Recording[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setRecordings(await fetchRecordings())
    } catch { /* backend might not be up yet */ }
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <div className="max-w-2xl mx-auto py-8 space-y-6 px-4">
      <h1 className="text-3xl font-bold text-center">mini_mal</h1>
      <p className="text-center text-gray-500">面试复盘工具</p>

      <div className="grid gap-6">
        <UploadForm onUploaded={load} />
        <AudioRecorder onRecorded={load} />
        <RecordingList recordings={recordings} loading={loading} />
      </div>
    </div>
  )
}
