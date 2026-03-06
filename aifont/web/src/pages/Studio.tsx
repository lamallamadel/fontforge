import { useParams } from 'react-router-dom';
import { GlyphEditor } from '../components/studio/GlyphEditor';
import { GlyphList } from '../components/studio/GlyphList';
import { PropertiesPanel } from '../components/studio/PropertiesPanel';
import { Toolbar } from '../components/studio/Toolbar';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { useProject } from '../hooks/useProject';
import { useProjectStore } from '../store/projectStore';

export function Studio() {
  const { projectId } = useParams<{ projectId: string }>();
  const { activeProject, loading } = useProject(projectId);
  const { activeGlyph, activeTool, setActiveTool } = useProjectStore();

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!activeProject) {
    return (
      <div className="flex h-full items-center justify-center text-gray-600">
        Project not found
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <Toolbar
        activeTool={activeTool}
        onToolChange={setActiveTool}
      />

      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar: glyph list */}
        <aside className="w-44 flex-shrink-0 overflow-y-auto border-r border-gray-800 bg-gray-900">
          <div className="border-b border-gray-800 px-3 py-2">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-500">
              Glyphs
            </h2>
          </div>
          <GlyphList glyphs={activeProject.glyphs} />
        </aside>

        {/* Center: editor canvas */}
        <main className="flex-1 overflow-hidden">
          <GlyphEditor glyph={activeGlyph} tool={activeTool} />
        </main>

        {/* Right sidebar: properties */}
        <aside className="w-52 flex-shrink-0 overflow-y-auto border-l border-gray-800 bg-gray-900">
          <div className="border-b border-gray-800 px-3 py-2">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-500">
              Properties
            </h2>
          </div>
          <PropertiesPanel glyph={activeGlyph} />
        </aside>
      </div>
    </div>
  );
}
