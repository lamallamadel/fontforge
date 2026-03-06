import type { Glyph } from '../../api/types';
import { useProjectStore } from '../../store/projectStore';

interface GlyphListProps {
  glyphs: Glyph[];
}

export function GlyphList({ glyphs }: GlyphListProps) {
  const { activeGlyph, setActiveGlyph } = useProjectStore();

  if (glyphs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 p-6 text-center text-gray-600">
        <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <p className="text-xs">No glyphs yet</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-px overflow-y-auto" data-testid="glyph-list">
      {glyphs.map((glyph) => {
        const isActive = activeGlyph?.id === glyph.id;
        return (
          <button
            key={glyph.id}
            onClick={() => setActiveGlyph(glyph)}
            className={[
              'flex items-center gap-3 px-3 py-2 text-left text-sm transition-colors',
              isActive
                ? 'bg-indigo-600/20 text-white'
                : 'text-gray-400 hover:bg-gray-800 hover:text-white',
            ].join(' ')}
          >
            <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded bg-gray-700 font-mono text-base font-medium text-white">
              {glyph.char}
            </span>
            <div className="min-w-0">
              <p className="truncate font-medium text-xs">{glyph.name}</p>
              <p className="text-xs text-gray-600">U+{glyph.unicode.toString(16).toUpperCase().padStart(4, '0')}</p>
            </div>
          </button>
        );
      })}
    </div>
  );
}
