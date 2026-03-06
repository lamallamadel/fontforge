import type { Glyph } from '../../api/types';

interface PropertiesPanelProps {
  glyph: Glyph | null;
  onChange?: (glyph: Glyph) => void;
}

function Field({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-medium text-gray-500">{label}</label>
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="rounded border border-gray-700 bg-gray-800 px-2 py-1.5 text-sm text-white focus:border-indigo-500 focus:outline-none"
      />
    </div>
  );
}

export function PropertiesPanel({ glyph, onChange }: PropertiesPanelProps) {
  if (!glyph) {
    return (
      <div className="flex items-center justify-center p-6 text-xs text-gray-600">
        Select a glyph to see properties
      </div>
    );
  }

  const update = (key: keyof Glyph) => (val: number) => {
    if (onChange) onChange({ ...glyph, [key]: val });
  };

  return (
    <div className="flex flex-col gap-4 p-4" data-testid="properties-panel">
      {/* Glyph identity */}
      <div className="flex items-center gap-3 rounded-lg bg-gray-800 p-3">
        <span className="flex h-10 w-10 items-center justify-center rounded bg-gray-700 font-mono text-xl font-bold text-white">
          {glyph.char}
        </span>
        <div>
          <p className="text-sm font-semibold text-white">{glyph.name}</p>
          <p className="text-xs text-gray-500">
            U+{glyph.unicode.toString(16).toUpperCase().padStart(4, '0')}
          </p>
        </div>
      </div>

      {/* Metrics */}
      <section>
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
          Metrics
        </h3>
        <div className="grid grid-cols-2 gap-2">
          <Field label="Width" value={glyph.width} onChange={update('width')} />
          <Field label="Height" value={glyph.height} onChange={update('height')} />
          <Field label="LSB" value={glyph.lsb} onChange={update('lsb')} />
          <Field label="RSB" value={glyph.rsb} onChange={update('rsb')} />
        </div>
      </section>

      {/* Path info */}
      <section>
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
          Path Info
        </h3>
        <div className="flex flex-col gap-1.5 text-sm text-gray-400">
          <div className="flex justify-between">
            <span>Contours</span>
            <span className="text-white">{glyph.contours.length}</span>
          </div>
          <div className="flex justify-between">
            <span>Points</span>
            <span className="text-white">
              {glyph.contours.reduce((s, c) => s + c.points.length, 0)}
            </span>
          </div>
        </div>
      </section>
    </div>
  );
}
