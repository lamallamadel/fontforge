import type { PreviewMode } from '../../api/types';

interface FontPreviewProps {
  text: string;
  fontSize: number;
  letterSpacing: number;
  mode: PreviewMode;
  fontFamily?: string;
}

const ALPHABET = 'AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz';
const WATERFALL_SIZES = [72, 60, 48, 36, 24, 18, 14];
const SAMPLE_SENTENCE = 'The quick brown fox jumps over the lazy dog';

export function FontPreview({
  text,
  fontSize,
  letterSpacing,
  mode,
  fontFamily = 'system-ui',
}: FontPreviewProps) {
  const style: React.CSSProperties = {
    fontFamily,
    letterSpacing: `${letterSpacing}em`,
  };

  if (mode === 'waterfall') {
    return (
      <div className="flex flex-col gap-4 p-6" data-testid="font-preview" data-mode="waterfall">
        {WATERFALL_SIZES.map((size) => (
          <div key={size} className="flex items-baseline gap-4 border-b border-gray-800 pb-4">
            <span className="w-10 flex-shrink-0 text-xs text-gray-600">{size}px</span>
            <span
              style={{ ...style, fontSize: `${size}px` }}
              className="text-white leading-none"
            >
              {SAMPLE_SENTENCE}
            </span>
          </div>
        ))}
      </div>
    );
  }

  if (mode === 'alphabet') {
    return (
      <div className="p-6" data-testid="font-preview" data-mode="alphabet">
        <div
          style={{ ...style, fontSize: `${fontSize}px` }}
          className="text-white leading-relaxed tracking-wide"
        >
          {ALPHABET.split('').map((char, i) => (
            <span key={i} className="inline-block mr-2 mb-2">
              {char}
            </span>
          ))}
        </div>
        <div
          style={{ ...style, fontSize: `${Math.round(fontSize * 0.6)}px` }}
          className="mt-6 text-gray-400"
        >
          0123456789 !@#$%^&amp;*()_+=-[]{}|;':",&lt;&gt;?/
        </div>
      </div>
    );
  }

  // sentence mode
  return (
    <div className="flex flex-col gap-6 p-6" data-testid="font-preview" data-mode="sentence">
      <p
        style={{ ...style, fontSize: `${fontSize}px` }}
        className="text-white leading-relaxed"
      >
        {text || SAMPLE_SENTENCE}
      </p>
      <p
        style={{ ...style, fontSize: `${Math.round(fontSize * 0.6)}px` }}
        className="text-gray-300 leading-relaxed"
      >
        {text || SAMPLE_SENTENCE}
      </p>
      <p
        style={{ ...style, fontSize: `${Math.round(fontSize * 0.35)}px` }}
        className="text-gray-500 leading-relaxed"
      >
        {text || SAMPLE_SENTENCE}
      </p>
    </div>
  );
}
