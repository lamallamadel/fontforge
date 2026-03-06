import type { PromptHistoryItem } from '../../api/types';

interface PromptHistoryProps {
  items: PromptHistoryItem[];
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function PromptHistory({ items }: PromptHistoryProps) {
  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 py-8 text-center text-gray-600">
        <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
        <p className="text-xs">No prompts yet. Start generating!</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3" data-testid="prompt-history">
      {items.map((item) => (
        <div
          key={item.id}
          className="rounded-xl border border-gray-700 bg-gray-800 p-4 text-sm"
        >
          <div className="mb-2 flex items-start justify-between gap-2">
            <p className="font-medium text-white">{item.prompt}</p>
            <span className="flex-shrink-0 text-xs text-gray-600">
              {formatTime(item.timestamp)}
            </span>
          </div>

          {item.response && (
            <div className="mt-2 rounded-lg bg-gray-900 p-3">
              <div className="mb-1 flex items-center gap-2">
                <span
                  className={[
                    'rounded-full px-2 py-0.5 text-xs font-medium',
                    item.response.status === 'completed'
                      ? 'bg-green-900/50 text-green-400'
                      : item.response.status === 'failed'
                      ? 'bg-red-900/50 text-red-400'
                      : 'bg-yellow-900/50 text-yellow-400',
                  ].join(' ')}
                >
                  {item.response.status}
                </span>
                {item.response.result && (
                  <span className="text-xs text-gray-500">
                    {Math.round(item.response.result.confidence * 100)}% confidence
                  </span>
                )}
              </div>
              {item.response.result && (
                <p className="text-xs text-gray-400">{item.response.result.message}</p>
              )}
              {item.response.error && (
                <p className="text-xs text-red-400">{item.response.error}</p>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
