import { useState, useEffect, useCallback } from 'react';
import { fontApi } from '../api/client';
import type { FontProject, CreateFontRequest } from '../api/types';
import { useProjectStore } from '../store/projectStore';

export function useProject(projectId?: string) {
  const { projects, setProjects, addProject, removeProject, updateProject, setActiveProject, activeProject } =
    useProjectStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadProjects = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fontApi.listFonts();
      setProjects(data);
    } catch (e) {
      setError('Failed to load projects');
    } finally {
      setLoading(false);
    }
  }, [setProjects]);

  const loadProject = useCallback(
    async (id: string) => {
      setLoading(true);
      setError(null);
      try {
        const data = await fontApi.getFont(id);
        setActiveProject(data);
        updateProject(id, data);
      } catch (e) {
        setError('Failed to load project');
      } finally {
        setLoading(false);
      }
    },
    [setActiveProject, updateProject]
  );

  const createProject = useCallback(
    async (data: CreateFontRequest): Promise<FontProject | null> => {
      setLoading(true);
      setError(null);
      try {
        const project = await fontApi.createFont(data);
        addProject(project);
        return project;
      } catch (e) {
        setError('Failed to create project');
        return null;
      } finally {
        setLoading(false);
      }
    },
    [addProject]
  );

  const deleteProject = useCallback(
    async (id: string) => {
      try {
        await fontApi.deleteFont(id);
        removeProject(id);
      } catch (e) {
        setError('Failed to delete project');
      }
    },
    [removeProject]
  );

  useEffect(() => {
    if (projectId && (!activeProject || activeProject.id !== projectId)) {
      loadProject(projectId);
    }
  }, [projectId, activeProject, loadProject]);

  return {
    projects,
    activeProject,
    loading,
    error,
    loadProjects,
    loadProject,
    createProject,
    deleteProject,
  };
}
