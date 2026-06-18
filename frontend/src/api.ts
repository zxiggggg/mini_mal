const BASE = '/api'

export interface Recording {
  id: string
  filename: string
  source_type: 'video_call' | 'direct_recording'
  file_path: string
  duration: number | null
  created_at: string
}

export async function fetchRecordings(): Promise<Recording[]> {
  const res = await fetch(`${BASE}/recordings`)
  if (!res.ok) throw new Error('Failed to fetch recordings')
  return res.json()
}

export async function uploadRecording(file: File, sourceType: string): Promise<Recording> {
  const form = new FormData()
  form.append('file', file)
  form.append('source_type', sourceType)
  const res = await fetch(`${BASE}/recordings/upload`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function saveRecording(blob: Blob, sourceType: string): Promise<Recording> {
  const form = new FormData()
  form.append('source_type', sourceType)
  const reader = new FileReader()
  const base64: string = await new Promise((resolve) => {
    reader.onloadend = () => resolve(reader.result as string)
    reader.readAsDataURL(blob)
  })
  form.append('blob', base64)
  const res = await fetch(`${BASE}/recordings/record`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
