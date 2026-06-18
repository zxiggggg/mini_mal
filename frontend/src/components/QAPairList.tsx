import type { QAPair } from '../api'

interface Props {
  qaPairs: QAPair[]
}

export default function QAPairList({ qaPairs }: Props) {
  if (qaPairs.length === 0) return <p className="text-gray-400">暂无问答对</p>

  return (
    <div className="space-y-4">
      <h3 className="font-semibold text-lg">问答对</h3>
      {qaPairs.map((qa, i) => (
        <div key={qa.id || i} className="border rounded-lg overflow-hidden">
          <div className="bg-blue-50 px-4 py-3">
            <p className="text-xs text-blue-500 font-medium mb-1">问题 {i + 1}</p>
            <p className="text-sm text-gray-800">{qa.question}</p>
          </div>
          <div className="bg-green-50 px-4 py-3">
            <p className="text-xs text-green-500 font-medium mb-1">回答</p>
            <p className="text-sm text-gray-800">{qa.answer}</p>
          </div>
        </div>
      ))}
    </div>
  )
}
