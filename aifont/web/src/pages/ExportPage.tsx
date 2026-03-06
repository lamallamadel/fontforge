import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { ExportPanel } from '../components/export/ExportPanel';
import { ExportHistory } from '../components/export/ExportHistory';
import { exportApi } from '../api/client';
import type { ExportFormat, ExportOptions, ExportResult } from '../api/types';

export function ExportPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [exports, setExports] = useState<ExportResult[]>([]);

  const handleExport = async (
    format: ExportFormat,
    options: ExportOptions
  ): Promise<ExportResult | null> => {
    if (!projectId) return null;
    const result = await exportApi.exportFont({
      fontId: projectId,
      format,
      options,
    });
    if (result) {
      setExports((prev) => [result, ...prev]);
    }
    return result;
  };

  return (
    <div className="flex h-full flex-col lg:flex-row">
      {/* Main export panel */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mb-6">
          <h1 className="text-xl font-bold text-white">Export Font</h1>
          <p className="mt-0.5 text-sm text-gray-400">
            Export your font in various formats
          </p>
        </div>

        <div className="max-w-xl">
          <ExportPanel
            fontId={projectId ?? ''}
            onExport={handleExport}
          />
        </div>
      </div>

      {/* History sidebar */}
      <div className="w-full overflow-y-auto border-t border-gray-800 p-4 lg:w-80 lg:border-l lg:border-t-0">
        <h2 className="mb-4 text-sm font-semibold text-gray-400">Export History</h2>
        <ExportHistory exports={exports} />
      </div>
    </div>
  );
}
