import { useState, useRef } from 'react';
import { Button } from '../common/Button';

interface PromptInputProps {
  onSubmit: (prompt: string) => Promise<void>;
  loading: boolean;
}

const SUGGESTIONS = [
  'Create a bold geometric letter A',
  'Generate a lowercase g with a double-story design',
  'Make the letter O more circular with optical corrections',
  'Create a set of punctuation marks in a modern style',
];

export function PromptInput({ onSubmit, loading }: PromptInputProps) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) return;
    await onSubmit(trimmed);
    setValue('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3" data-testid="prompt-form">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Describe the glyph you want to create or modify… (Ctrl+Enter to send)"
        rows={4}
        disabled={loading}
        className="w-full resize-none rounded-xl border border-gray-700 bg-gray-800 px-4 py-3 text-sm text-white placeholder-gray-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-50"
        data-testid="prompt-input"
      />

      {/* Suggestions */}
      <div className="flex flex-wrap gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setValue(s)}
            className="rounded-full border border-gray-700 bg-gray-800 px-3 py-1 text-xs text-gray-400 transition-colors hover:border-indigo-500/50 hover:text-indigo-300"
          >
            {s}
          </button>
        ))}
      </div>

      <div className="flex items-center justify-between">
        <p className="text-xs text-gray-600">{value.length} chars · Ctrl+Enter to send</p>
        <Button type="submit" loading={loading} disabled={!value.trim()}>
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
          Generate
        </Button>
      </div>
    </form>
  );
}
