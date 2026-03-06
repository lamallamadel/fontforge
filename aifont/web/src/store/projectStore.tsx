import React, { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import type { FontProject, Glyph, Tool, PromptHistoryItem } from '../api/types';

interface ProjectContextValue {
  projects: FontProject[];
  activeProject: FontProject | null;
  activeGlyph: Glyph | null;
  activeTool: Tool;
  promptHistory: PromptHistoryItem[];
  setProjects: React.Dispatch<React.SetStateAction<FontProject[]>>;
  setActiveProject: (project: FontProject | null) => void;
  setActiveGlyph: (glyph: Glyph | null) => void;
  setActiveTool: (tool: Tool) => void;
  addProject: (project: FontProject) => void;
  removeProject: (id: string) => void;
  updateProject: (id: string, updates: Partial<FontProject>) => void;
  addPromptHistory: (item: PromptHistoryItem) => void;
}

const ProjectContext = createContext<ProjectContextValue | null>(null);

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [projects, setProjects] = useState<FontProject[]>([]);
  const [activeProject, setActiveProject] = useState<FontProject | null>(null);
  const [activeGlyph, setActiveGlyph] = useState<Glyph | null>(null);
  const [activeTool, setActiveTool] = useState<Tool>('select');
  const [promptHistory, setPromptHistory] = useState<PromptHistoryItem[]>([]);

  const addProject = useCallback((project: FontProject) => {
    setProjects((prev) => [project, ...prev]);
  }, []);

  const removeProject = useCallback((id: string) => {
    setProjects((prev) => prev.filter((p) => p.id !== id));
    setActiveProject((prev) => (prev?.id === id ? null : prev));
  }, []);

  const updateProject = useCallback((id: string, updates: Partial<FontProject>) => {
    setProjects((prev) =>
      prev.map((p) => (p.id === id ? { ...p, ...updates } : p))
    );
    setActiveProject((prev) =>
      prev?.id === id ? { ...prev, ...updates } : prev
    );
  }, []);

  const addPromptHistory = useCallback((item: PromptHistoryItem) => {
    setPromptHistory((prev) => [item, ...prev]);
  }, []);

  return (
    <ProjectContext.Provider
      value={{
        projects,
        activeProject,
        activeGlyph,
        activeTool,
        promptHistory,
        setProjects,
        setActiveProject,
        setActiveGlyph,
        setActiveTool,
        addProject,
        removeProject,
        updateProject,
        addPromptHistory,
      }}
    >
      {children}
    </ProjectContext.Provider>
  );
}

export function useProjectStore(): ProjectContextValue {
  const ctx = useContext(ProjectContext);
  if (!ctx) throw new Error('useProjectStore must be used within ProjectProvider');
  return ctx;
}
