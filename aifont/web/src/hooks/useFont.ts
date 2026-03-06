import { useState, useCallback } from 'react';
import { fontApi } from '../api/client';
import type { FontProject } from '../api/types';
import { useProjectStore } from '../store/projectStore';

export function useFont() {
  const { activeProject, setActiveProject } = useProjectStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchFont = useCallback(
    async (id: string): Promise<FontProject | null> => {
      setLoading(true);
      setError(null);
      try {
        const data = await fontApi.getFont(id);
        setActiveProject(data);
        return data;
      } catch {
        setError('Failed to fetch font');
        return null;
      } finally {
        setLoading(false);
      }
    },
    [setActiveProject]
  );

  return {
    font: activeProject,
    loading,
    error,
    fetchFont,
  };
}
