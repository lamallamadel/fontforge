import type { ExportResult } from '../../api/types';

interface ExportHistoryProps {
  exports: ExportResult[];
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

const FORMAT_BADGES: Record<string, string> = {
  otf: 'bg-blue-500/20 text-blue-300',
  ttf: 'bg-green-500/20 text-green-300',
  woff2: 'bg-purple-500/20 text-purple-300',
  svg: 'bg-amber-500/20 text-amber-300',
};

export function ExportHistory({ exports }: ExportHistoryProps) {
  if (exports.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 py-8 text-center text-gray-600">
        <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        <p className="text-xs">No exports yet</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2" data-testid="export-history">
      {exports.map((exp) => (
        <div
          key={exp.id}
          className="flex items-center justify-between rounded-lg border border-gray-700 bg-gray-800 px-4 py-3"
        >
          <div className="flex items-center gap-3">
            <span className={[
              'rounded-full px-2 py-0.5 text-xs font-bold uppercase',
              FORMAT_BADGES[exp.format] ?? 'bg-gray-700 text-gray-300',
            ].join(' ')}>
              {exp.format}
            </span>
            <div>
              <p className="text-sm text-white">{formatBytes(exp.size)}</p>
              <p className="text-xs text-gray-500">{formatDate(exp.createdAt)}</p>
            </div>
          </div>
          <a
            href={exp.url}
            download
            className="rounded-lg border border-gray-600 px-3 py-1.5 text-xs text-gray-400 transition-colors hover:border-indigo-500/50 hover:text-indigo-300"
          >
            Download
          </a>
        </div>
      ))}
    </div>
  );
}
