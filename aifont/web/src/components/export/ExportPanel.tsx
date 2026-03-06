import { useState } from 'react';
import { Button } from '../common/Button';
import type { ExportFormat, ExportOptions, ExportResult } from '../../api/types';

interface ExportPanelProps {
  fontId: string;
  onExport: (format: ExportFormat, options: ExportOptions) => Promise<ExportResult | null>;
}

const FORMAT_INFO: Record<ExportFormat, { label: string; description: string; color: string }> = {
  otf: {
    label: 'OTF',
    description: 'OpenType — best for desktop use',
    color: 'text-blue-400',
  },
  ttf: {
    label: 'TTF',
    description: 'TrueType — broad compatibility',
    color: 'text-green-400',
  },
  woff2: {
    label: 'WOFF2',
    description: 'Web font — compressed for web',
    color: 'text-purple-400',
  },
  svg: {
    label: 'SVG',
    description: 'SVG font — legacy web support',
    color: 'text-amber-400',
  },
};

export function ExportPanel({ onExport }: ExportPanelProps) {
  const [format, setFormat] = useState<ExportFormat>('otf');
  const [options, setOptions] = useState<ExportOptions>({
    hinting: true,
    optimize: true,
    includeMetadata: true,
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ExportResult | null>(null);

  const handleExport = async () => {
    setLoading(true);
    setResult(null);
    const r = await onExport(format, options);
    setResult(r);
    setLoading(false);
  };

  return (
    <div className="flex flex-col gap-6" data-testid="export-panel">
      {/* Format selection */}
      <section>
        <h3 className="mb-3 text-sm font-semibold text-gray-300">Export Format</h3>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {(Object.keys(FORMAT_INFO) as ExportFormat[]).map((f) => {
            const info = FORMAT_INFO[f];
            const isActive = format === f;
            return (
              <button
                key={f}
                onClick={() => setFormat(f)}
                data-format={f}
                className={[
                  'flex flex-col gap-1 rounded-xl border p-3 text-left transition-colors',
                  isActive
                    ? 'border-indigo-500/50 bg-indigo-600/10'
                    : 'border-gray-700 bg-gray-800 hover:border-gray-600',
                ].join(' ')}
              >
                <span className={`text-lg font-bold ${info.color}`}>{info.label}</span>
                <span className="text-xs text-gray-500">{info.description}</span>
              </button>
            );
          })}
        </div>
      </section>

      {/* Options */}
      <section>
        <h3 className="mb-3 text-sm font-semibold text-gray-300">Export Options</h3>
        <div className="flex flex-col gap-2">
          {[
            { key: 'hinting' as const, label: 'Enable Hinting', description: 'Optimize rendering at small sizes' },
            { key: 'optimize' as const, label: 'Optimize File Size', description: 'Compress and optimize output' },
            { key: 'includeMetadata' as const, label: 'Include Metadata', description: 'Embed name, copyright, and version' },
          ].map(({ key, label, description }) => (
            <label
              key={key}
              className="flex cursor-pointer items-center gap-3 rounded-lg border border-gray-700 bg-gray-800 p-3 hover:border-gray-600 transition-colors"
            >
              <input
                type="checkbox"
                checked={options[key] ?? false}
                onChange={(e) => setOptions((o) => ({ ...o, [key]: e.target.checked }))}
                className="h-4 w-4 rounded border-gray-600 bg-gray-700 text-indigo-600 accent-indigo-500"
              />
              <div>
                <p className="text-sm font-medium text-white">{label}</p>
                <p className="text-xs text-gray-500">{description}</p>
              </div>
            </label>
          ))}
        </div>
      </section>

      {/* Subset */}
      <section>
        <h3 className="mb-2 text-sm font-semibold text-gray-300">Character Subset (optional)</h3>
        <input
          type="text"
          placeholder="Leave empty for all glyphs, or enter chars: ABCabc123"
          value={options.subset ?? ''}
          onChange={(e) => setOptions((o) => ({ ...o, subset: e.target.value || undefined }))}
          className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-indigo-500 focus:outline-none"
        />
      </section>

      {/* Export button */}
      <Button onClick={handleExport} loading={loading} size="lg" className="w-full">
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        Export as {FORMAT_INFO[format].label}
      </Button>

      {/* Result */}
      {result && (
        <div className="rounded-xl border border-green-500/30 bg-green-950/30 p-4">
          <div className="mb-2 flex items-center gap-2">
            <svg className="h-4 w-4 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span className="text-sm font-medium text-green-400">Export Complete</span>
          </div>
          <div className="flex items-center justify-between text-xs text-gray-400">
            <span>{(result.size / 1024).toFixed(1)} KB</span>
            <a
              href={result.url}
              download
              className="text-indigo-400 hover:text-indigo-300 transition-colors"
            >
              Download ↓
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
