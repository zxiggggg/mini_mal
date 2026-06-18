const BASE = '/api'

export interface Recording {
  id: string
  filename: string
  source_type: 'video_call' | 'direct_recording'
  file_path: string
  duration: number | null
  created_at: string
}

export interface Transcription {
  id: string
  recording_id: string
  text: string | null
  speaker_labels: Record<string, string> | null
  status: 'pending' | 'processing' | 'done' | 'error'
  error_message: string | null
  created_at: string
}

export interface QAPair {
  id: string
  transcription_id: string
  question: string
  answer: string
  order_index: number
  suggestions: string[] | null
  created_at: string
}

export interface QAPairList {
  qa_pairs: QAPair[]
  speaker_labels: Record<string, string> | null
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
  const base64: string = await new Promise((resolve) => {
    const reader = new FileReader()
    reader.onloadend = () => resolve(reader.result as string)
    reader.readAsDataURL(blob)
  })
  form.append('blob', base64)
  const res = await fetch(`${BASE}/recordings/record`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function startTranscribe(recordingId: string): Promise<Transcription> {
  const res = await fetch(`${BASE}/recordings/${recordingId}/transcribe`, { method: 'POST' })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getTranscription(recordingId: string): Promise<Transcription> {
  const res = await fetch(`${BASE}/recordings/${recordingId}/transcription`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function updateTranscription(recordingId: string, text: string): Promise<Transcription> {
  const res = await fetch(`${BASE}/recordings/${recordingId}/transcription`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function updateSpeakerLabels(recordingId: string, speakerLabels: Record<string, string>): Promise<Transcription> {
  const res = await fetch(`${BASE}/recordings/${recordingId}/speakers`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ speaker_labels: speakerLabels }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function extractQAPairs(recordingId: string): Promise<QAPairList> {
  const res = await fetch(`${BASE}/recordings/${recordingId}/qa-pairs`, { method: 'POST' })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function fetchQAPairs(recordingId: string): Promise<QAPairList> {
  const res = await fetch(`${BASE}/recordings/${recordingId}/qa-pairs`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function generateSuggestions(recordingId: string): Promise<QAPairList> {
  const res = await fetch(`${BASE}/recordings/${recordingId}/suggestions`, { method: 'POST' })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
