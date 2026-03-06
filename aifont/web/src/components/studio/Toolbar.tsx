import type { Tool } from '../../api/types';

interface ToolbarProps {
  activeTool: Tool;
  onToolChange: (tool: Tool) => void;
  onNewContour?: () => void;
  onDeleteSelected?: () => void;
}

interface ToolDef {
  id: Tool;
  label: string;
  shortcut: string;
  icon: React.ReactNode;
}

const TOOLS: ToolDef[] = [
  {
    id: 'select',
    label: 'Select',
    shortcut: 'V',
    icon: (
      <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
          d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5" />
      </svg>
    ),
  },
  {
    id: 'pen',
    label: 'Pen',
    shortcut: 'P',
    icon: (
      <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
          d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
      </svg>
    ),
  },
  {
    id: 'zoom',
    label: 'Zoom',
    shortcut: 'Z',
    icon: (
      <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
          d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
      </svg>
    ),
  },
];

export function Toolbar({ activeTool, onToolChange, onNewContour, onDeleteSelected }: ToolbarProps) {
  return (
    <div
      className="flex items-center gap-1 border-b border-gray-800 bg-gray-950 px-3 py-2"
      role="toolbar"
      aria-label="Drawing tools"
      data-testid="toolbar"
    >
      {TOOLS.map((t) => (
        <button
          key={t.id}
          onClick={() => onToolChange(t.id)}
          title={`${t.label} (${t.shortcut})`}
          aria-pressed={activeTool === t.id}
          className={[
            'flex h-8 w-8 items-center justify-center rounded-lg transition-colors',
            activeTool === t.id
              ? 'bg-indigo-600 text-white'
              : 'text-gray-400 hover:bg-gray-800 hover:text-white',
          ].join(' ')}
        >
          {t.icon}
        </button>
      ))}

      <div className="mx-2 h-5 w-px bg-gray-700" />

      <button
        onClick={onNewContour}
        title="New contour"
        className="flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs text-gray-400 hover:bg-gray-800 hover:text-white transition-colors"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
        </svg>
        Contour
      </button>

      <button
        onClick={onDeleteSelected}
        title="Delete selected"
        className="flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs text-gray-400 hover:bg-gray-800 hover:text-red-400 transition-colors"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
        </svg>
        Delete
      </button>
    </div>
  );
}
