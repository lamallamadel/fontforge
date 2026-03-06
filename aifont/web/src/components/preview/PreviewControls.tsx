import type { PreviewMode } from '../../api/types';

interface PreviewControlsProps {
  fontSize: number;
  letterSpacing: number;
  mode: PreviewMode;
  onFontSizeChange: (v: number) => void;
  onLetterSpacingChange: (v: number) => void;
  onModeChange: (m: PreviewMode) => void;
}

const MODES: { id: PreviewMode; label: string }[] = [
  { id: 'sentence', label: 'Sentence' },
  { id: 'waterfall', label: 'Waterfall' },
  { id: 'alphabet', label: 'Alphabet' },
];

export function PreviewControls({
  fontSize,
  letterSpacing,
  mode,
  onFontSizeChange,
  onLetterSpacingChange,
  onModeChange,
}: PreviewControlsProps) {
  return (
    <div
      className="flex flex-wrap items-center gap-4 border-b border-gray-800 bg-gray-900 px-6 py-3"
      data-testid="preview-controls"
    >
      {/* Mode tabs */}
      <div className="flex rounded-lg border border-gray-700 bg-gray-800 p-0.5">
        {MODES.map((m) => (
          <button
            key={m.id}
            onClick={() => onModeChange(m.id)}
            className={[
              'rounded-md px-3 py-1 text-xs font-medium transition-colors',
              mode === m.id
                ? 'bg-indigo-600 text-white'
                : 'text-gray-400 hover:text-white',
            ].join(' ')}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Font size */}
      <div className="flex items-center gap-2">
        <label className="text-xs text-gray-500 whitespace-nowrap">Size</label>
        <input
          type="range"
          min={12}
          max={200}
          value={fontSize}
          onChange={(e) => onFontSizeChange(Number(e.target.value))}
          className="w-28 accent-indigo-500"
          data-testid="font-size-slider"
        />
        <span className="w-10 text-xs text-gray-400 text-right">{fontSize}px</span>
      </div>

      {/* Letter spacing */}
      <div className="flex items-center gap-2">
        <label className="text-xs text-gray-500 whitespace-nowrap">Spacing</label>
        <input
          type="range"
          min={-0.1}
          max={0.5}
          step={0.01}
          value={letterSpacing}
          onChange={(e) => onLetterSpacingChange(Number(e.target.value))}
          className="w-24 accent-indigo-500"
          data-testid="letter-spacing-slider"
        />
        <span className="w-12 text-xs text-gray-400 text-right">
          {letterSpacing.toFixed(2)}em
        </span>
      </div>
    </div>
  );
}
