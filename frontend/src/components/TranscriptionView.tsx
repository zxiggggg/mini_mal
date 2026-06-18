import { useEffect, useMemo, useState } from 'react'
import {
  autoQaPreview,
  extractQAPairs,
  fetchQAPairs,
  generateSuggestions,
  getTranscription,
  startTranscribe,
  updateSpeakerLabels,
  updateTranscription,
  type AutoQAPairPreview,
  type QAPair,
  type Transcription,
} from '../api'
import QAPairList from './QAPairList'

type DialogueTurn = {
  speakerId: string
  role: string
  text: string
  isQuestion: boolean
}

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

  // Speaker labeling
  const [speakerLabels, setSpeakerLabels] = useState<Record<string, string>>({})
  const [qaPairs, setQaPairs] = useState<QAPair[]>([])
  const [autoPreview, setAutoPreview] = useState<AutoQAPairPreview[]>([])
  const [extracting, setExtracting] = useState(false)
  const [generating, setGenerating] = useState(false)

  // Parse unique speakers from transcript text
  const speakers = useMemo(() => {
    const text = transcription?.text || ''
    const seen = new Set<string>()
    const ids: string[] = []
    for (const m of text.matchAll(/\[说话人 (\S+)\]/g)) {
      if (!seen.has(m[1])) {
        seen.add(m[1])
        ids.push(m[1])
      }
    }
    return ids
  }, [transcription?.text])

  const dialogueTurns = useMemo(() => {
    const text = transcription?.text || ''
    const turns: DialogueTurn[] = []
    const blocks = text.split(/\n\s*\n/).map(part => part.trim()).filter(Boolean)

    let currentTurn: DialogueTurn | null = null

    const flushCurrentTurn = () => {
      if (currentTurn) {
        turns.push(currentTurn)
        currentTurn = null
      }
    }

    for (const block of blocks) {
      const match = block.match(/^\[说话人 (\S+)\]\s*(.*)$/s)
      if (!match) continue

      const speakerId = match[1]
      const content = match[2].trim()
      const role = speakerLabels[speakerId] || speakerId
      const isQuestion = role === 'interviewer'

      if (currentTurn && currentTurn.speakerId === speakerId) {
        currentTurn.text = `${currentTurn.text}\n\n${content}`
        continue
      }

      flushCurrentTurn()
      currentTurn = { speakerId, role, text: content, isQuestion }
    }

    flushCurrentTurn()
    return turns
  }, [transcription?.text, speakerLabels])

  useEffect(() => {
    loadTranscription()
  }, [recordingId])

  const loadTranscription = async () => {
    try {
      const t = await getTranscription(recordingId)
      setTranscription(t)
      if (t.status === 'done' && t.text) {
        setEditText(t.text)
        if (t.speaker_labels) setSpeakerLabels(t.speaker_labels)
      }
      try {
        const qa = await fetchQAPairs(recordingId)
        setQaPairs(qa.qa_pairs)
      } catch { /* no qa pairs yet */ }
      try {
        const preview = await autoQaPreview(recordingId)
        setAutoPreview(preview.qa_pairs)
      } catch { /* no auto preview yet */ }
    } catch (_err) {
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

  const handleSaveText = async () => {
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

  const handleSaveLabels = async () => {
    setSaving(true)
    try {
      const t = await updateSpeakerLabels(recordingId, speakerLabels)
      setTranscription(t)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '保存标签失败')
    }
    setSaving(false)
  }

  const handleAutoQA = async () => {
    setExtracting(true)
    setError('')
    try {
      const result = await autoQaPreview(recordingId)
      setAutoPreview(result.qa_pairs)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '自动分析失败')
    }
    setExtracting(false)
  }

  const handleExtractQA = async () => {
    setExtracting(true)
    setError('')
    try {
      const result = await extractQAPairs(recordingId)
      setQaPairs(result.qa_pairs)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '提取失败')
    }
    setExtracting(false)
  }

  const handleGenerateSuggestions = async () => {
    setGenerating(true)
    setError('')
    try {
      const result = await generateSuggestions(recordingId)
      setQaPairs(result.qa_pairs)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '生成建议失败')
    }
    setGenerating(false)
  }

  const allLabeled = speakers.length > 0 && speakers.every(s => speakerLabels[s])

  if (loading) return <p className="text-gray-400 text-center py-8">加载中...</p>

  if (!transcription || transcription.status === 'pending') {
    return (
      <div className="bg-white rounded-lg shadow p-6 space-y-4 text-center">
        <h2 className="text-lg font-semibold">{filename}</h2>
        <p className="text-gray-400">尚未转写</p>
        {error && <p className="text-red-500 text-sm">{error}</p>}
        <button onClick={handleStart} className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700">
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
        <button onClick={handleStart} className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700">重试</button>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow p-6 space-y-6">
      <h2 className="text-lg font-semibold">{filename}</h2>

      {/* Transcript section */}
      <div className="space-y-2">
        <div className="flex justify-between items-center">
          <h3 className="font-medium text-sm text-gray-500">转写文本</h3>
          <div className="flex gap-2">
            {!editing ? (
              <button
                onClick={() => { setEditing(true); setEditText(transcription.text || '') }}
                className="text-blue-600 hover:underline text-sm"
              >编辑文本</button>
            ) : (
              <>
                <button onClick={() => setEditing(false)} className="text-gray-400 hover:underline text-sm">取消</button>
                <button onClick={handleSaveText} disabled={saving} className="text-blue-600 hover:underline text-sm disabled:opacity-50">
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
          <div className="space-y-3 max-h-96 overflow-y-auto pr-2">
            {dialogueTurns.length > 0 ? (
              dialogueTurns.map((turn, i) => {
                const isInterviewer = turn.role === 'interviewer'
                const badge = isInterviewer ? '面试官' : '面试者'
                const badgeColor = isInterviewer
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-green-100 text-green-700'
                return (
                  <div key={i} className={`flex gap-3 items-start ${turn.isQuestion ? 'bg-blue-50/60 rounded-lg p-3' : 'bg-green-50/60 rounded-lg p-3'}`}>
                    <span className={`shrink-0 px-2 py-0.5 rounded text-xs font-medium ${badgeColor}`}>
                      {badge}
                    </span>
                    <p className="text-gray-700 whitespace-pre-wrap leading-relaxed">{turn.text}</p>
                  </div>
                )
              })
            ) : (
              <p className="text-gray-500 text-sm whitespace-pre-wrap">{transcription.text || ''}</p>
            )}
          </div>
        )}
      </div>

      {/* Speaker labeling section */}
      {speakers.length > 0 && (
        <div className="border-t pt-4 space-y-3">
          <h3 className="font-medium text-sm text-gray-500">说话人角色标注</h3>
          <div className="space-y-2">
            {speakers.map(speakerId => (
              <div key={speakerId} className="flex items-center gap-3">
                <span className="text-sm w-20">{speakerId}</span>
                <label className="flex items-center gap-1 text-sm">
                  <input
                    type="radio"
                    name={`speaker-${speakerId}`}
                    checked={speakerLabels[speakerId] === 'interviewer'}
                    onChange={() => setSpeakerLabels(prev => ({ ...prev, [speakerId]: 'interviewer' }))}
                  />
                  面试官
                </label>
                <label className="flex items-center gap-1 text-sm">
                  <input
                    type="radio"
                    name={`speaker-${speakerId}`}
                    checked={speakerLabels[speakerId] === 'interviewee'}
                    onChange={() => setSpeakerLabels(prev => ({ ...prev, [speakerId]: 'interviewee' }))}
                  />
                  面试者
                </label>
              </div>
            ))}
          </div>
          <button
            onClick={handleSaveLabels}
            disabled={!allLabeled || saving}
            className="bg-gray-600 text-white px-4 py-1.5 rounded text-sm hover:bg-gray-700 disabled:opacity-50"
          >
            {saving ? '保存中...' : '保存标注'}
          </button>
        </div>
      )}

      {/* QA extraction section */}
      {allLabeled && (
        <div className="border-t pt-4 space-y-3">
          <h3 className="font-medium text-sm text-gray-500">问答对提取</h3>
          {autoPreview.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-xs text-gray-400">自动识别的问答结构预览</h4>
              <div className="space-y-2">
                {autoPreview.map((pair, i) => (
                  <div key={i} className="border rounded-lg p-3 bg-gray-50">
                    <p className="text-xs text-blue-500 font-medium mb-1">问题 {i + 1}</p>
                    <p className="text-sm text-gray-800 whitespace-pre-wrap mb-2">{pair.question}</p>
                    <p className="text-xs text-green-500 font-medium mb-1">回答</p>
                    <p className="text-sm text-gray-800 whitespace-pre-wrap">{pair.answer}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
          {qaPairs.length === 0 ? (
            <button
              onClick={handleExtractQA}
              disabled={extracting}
              className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {extracting ? '提取中...' : '提取问答对'}
            </button>
          ) : (
            <>
              <QAPairList qaPairs={qaPairs} />
              <div className="flex flex-wrap gap-4">
                <button
                  onClick={handleExtractQA}
                  disabled={extracting}
                  className="text-blue-600 hover:underline text-sm"
                >
                  {extracting ? '提取中...' : '重新提取'}
                </button>
                {!qaPairs.some(q => q.suggestions?.length) ? (
                  <button
                    onClick={handleGenerateSuggestions}
                    disabled={generating}
                    className="bg-amber-600 text-white px-4 py-1.5 rounded text-sm hover:bg-amber-700 disabled:opacity-50"
                  >
                    {generating ? '生成中...' : '生成建议'}
                  </button>
                ) : (
                  <button
                    onClick={handleGenerateSuggestions}
                    disabled={generating}
                    className="text-amber-600 hover:underline text-sm"
                  >
                    {generating ? '生成中...' : '重新生成建议'}
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {error && <p className="text-red-500 text-sm">{error}</p>}
    </div>
  )
}
