import type { AgentRunResponse } from '../../api/types';
import { Button } from '../common/Button';

interface PromptResultProps {
  result: AgentRunResponse | null;
  onApply?: () => void;
}

export function PromptResult({ result, onApply }: PromptResultProps) {
  if (!result) {
    return (
      <div className="rounded-xl border border-dashed border-gray-700 p-6 text-center text-sm text-gray-600">
        Generated result will appear here
      </div>
    );
  }

  const isComplete = result.status === 'completed';
  const isFailed = result.status === 'failed';

  return (
    <div
      className={[
        'rounded-xl border p-5',
        isComplete ? 'border-indigo-500/30 bg-indigo-950/30' : '',
        isFailed ? 'border-red-500/30 bg-red-950/30' : '',
        !isComplete && !isFailed ? 'border-gray-700 bg-gray-800' : '',
      ].join(' ')}
      data-testid="prompt-result"
    >
      <div className="mb-3 flex items-center gap-2">
        {isComplete && (
          <svg className="h-4 w-4 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        )}
        {isFailed && (
          <svg className="h-4 w-4 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        )}
        <h3 className="text-sm font-semibold text-white">
          {isComplete ? 'Generation Complete' : isFailed ? 'Generation Failed' : 'Processing…'}
        </h3>
      </div>

      {result.result && (
        <>
          <p className="mb-3 text-sm text-gray-300">{result.result.message}</p>
          <div className="mb-4 flex items-center gap-4 text-xs text-gray-500">
            <span>
              Confidence:{' '}
              <span className="text-indigo-300">
                {Math.round(result.result.confidence * 100)}%
              </span>
            </span>
            <span>
              Glyphs:{' '}
              <span className="text-white">{result.result.glyphs?.length ?? 0}</span>
            </span>
          </div>

          {/* Confidence bar */}
          <div className="mb-4 h-1.5 w-full overflow-hidden rounded-full bg-gray-700">
            <div
              className="h-full rounded-full bg-indigo-500 transition-all"
              style={{ width: `${result.result.confidence * 100}%` }}
            />
          </div>

          {isComplete && onApply && (
            <Button onClick={onApply} size="sm" className="w-full">
              Apply to Font
            </Button>
          )}
        </>
      )}

      {result.error && (
        <p className="text-sm text-red-400">{result.error}</p>
      )}
    </div>
  );
}
