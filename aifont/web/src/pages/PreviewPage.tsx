import { useState } from 'react';
import { FontPreview } from '../components/preview/FontPreview';
import { PreviewControls } from '../components/preview/PreviewControls';
import type { PreviewMode } from '../api/types';
import { useProjectStore } from '../store/projectStore';

const DEFAULT_TEXT = 'The quick brown fox jumps over the lazy dog';

export function PreviewPage() {
  const { activeProject } = useProjectStore();
  const [text, setText] = useState(DEFAULT_TEXT);
  const [fontSize, setFontSize] = useState(48);
  const [letterSpacing, setLetterSpacing] = useState(0);
  const [mode, setMode] = useState<PreviewMode>('sentence');

  return (
    <div className="flex h-full flex-col">
      <PreviewControls
        fontSize={fontSize}
        letterSpacing={letterSpacing}
        mode={mode}
        onFontSizeChange={setFontSize}
        onLetterSpacingChange={setLetterSpacing}
        onModeChange={setMode}
      />

      {/* Text input for sentence/alphabet modes */}
      {mode === 'sentence' && (
        <div className="border-b border-gray-800 bg-gray-900 px-6 py-3">
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Type preview text…"
            data-testid="preview-text-input"
            className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-indigo-500 focus:outline-none"
          />
        </div>
      )}

      {/* Preview area */}
      <div className="flex-1 overflow-y-auto bg-gray-950">
        {activeProject ? (
          <FontPreview
            text={text}
            fontSize={fontSize}
            letterSpacing={letterSpacing}
            mode={mode}
          />
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-gray-600">
            <svg className="h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="text-sm">
              Open a project to preview your font
            </p>

            {/* Demo preview without a real font */}
            <div className="mt-6 w-full max-w-2xl px-6">
              <FontPreview
                text={text}
                fontSize={fontSize}
                letterSpacing={letterSpacing}
                mode={mode}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
