import { Link } from 'react-router-dom';
import type { FontProject } from '../../api/types';

interface ProjectCardProps {
  project: FontProject;
  onDelete: (id: string) => void;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

const TAG_COLORS: Record<string, string> = {
  'sans-serif': 'bg-blue-500/20 text-blue-300',
  serif: 'bg-amber-500/20 text-amber-300',
  geometric: 'bg-purple-500/20 text-purple-300',
  humanist: 'bg-green-500/20 text-green-300',
  monospace: 'bg-gray-500/20 text-gray-300',
  code: 'bg-cyan-500/20 text-cyan-300',
};

export function ProjectCard({ project, onDelete }: ProjectCardProps) {
  return (
    <div
      data-testid="project-card"
      className="group relative flex flex-col rounded-xl border border-gray-700 bg-gray-800 p-5 transition-all hover:border-indigo-500/50 hover:shadow-lg hover:shadow-indigo-900/20"
    >
      {/* Thumbnail placeholder */}
      <div className="mb-4 flex h-32 items-center justify-center rounded-lg bg-gray-900 text-5xl font-bold text-gray-600 select-none">
        {project.name.charAt(0)}
      </div>

      <div className="flex-1">
        <h3 className="mb-1 font-semibold text-white">{project.name}</h3>
        <p className="mb-3 text-sm text-gray-400 line-clamp-2">{project.description}</p>

        <div className="mb-3 flex flex-wrap gap-1.5">
          {project.tags.map((tag) => (
            <span
              key={tag}
              className={[
                'rounded-full px-2 py-0.5 text-xs font-medium',
                TAG_COLORS[tag] ?? 'bg-gray-700 text-gray-300',
              ].join(' ')}
            >
              {tag}
            </span>
          ))}
        </div>

        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>{project.glyphCount} glyphs</span>
          <span>Updated {formatDate(project.updatedAt)}</span>
        </div>
      </div>

      <div className="mt-4 flex gap-2">
        <Link
          to={`/studio/${project.id}`}
          className="flex-1 rounded-lg bg-indigo-600 py-2 text-center text-sm font-medium text-white transition-colors hover:bg-indigo-500"
        >
          Open Studio
        </Link>
        <button
          onClick={() => onDelete(project.id)}
          aria-label={`Delete ${project.name}`}
          className="rounded-lg border border-gray-600 px-3 text-gray-400 transition-colors hover:border-red-500/50 hover:bg-red-900/20 hover:text-red-400"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>
    </div>
  );
}
