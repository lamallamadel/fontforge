import { useLocation, useParams, Link } from 'react-router-dom';
import { useProjectStore } from '../../store/projectStore';

export function Header() {
  const { activeProject } = useProjectStore();
  const location = useLocation();
  const { projectId } = useParams<{ projectId: string }>();

  const getBreadcrumbs = () => {
    const crumbs: { label: string; to?: string }[] = [
      { label: 'AIFont Studio', to: '/' },
    ];
    if (activeProject && projectId) {
      crumbs.push({ label: activeProject.name, to: `/studio/${projectId}` });
      if (location.pathname.endsWith('/prompt')) crumbs.push({ label: 'AI Prompt' });
      else if (location.pathname.endsWith('/preview')) crumbs.push({ label: 'Preview' });
      else if (location.pathname.endsWith('/export')) crumbs.push({ label: 'Export' });
      else crumbs.push({ label: 'Studio' });
    }
    return crumbs;
  };

  const crumbs = getBreadcrumbs();

  return (
    <header className="flex h-12 items-center justify-between border-b border-gray-800 bg-gray-950/80 px-4 backdrop-blur-sm">
      <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-sm">
        {crumbs.map((crumb, i) => (
          <span key={i} className="flex items-center gap-1.5">
            {i > 0 && <span className="text-gray-600">/</span>}
            {crumb.to && i < crumbs.length - 1 ? (
              <Link to={crumb.to} className="text-gray-400 hover:text-white transition-colors">
                {crumb.label}
              </Link>
            ) : (
              <span className={i === crumbs.length - 1 ? 'text-white font-medium' : 'text-gray-400'}>
                {crumb.label}
              </span>
            )}
          </span>
        ))}
      </nav>

      <div className="flex items-center gap-3">
        {activeProject && (
          <span className="hidden rounded-full bg-indigo-600/20 px-2.5 py-0.5 text-xs font-medium text-indigo-300 border border-indigo-500/30 sm:inline-flex">
            {activeProject.glyphCount} glyphs
          </span>
        )}
        <div className="h-7 w-7 rounded-full bg-indigo-600 flex items-center justify-center text-xs font-bold text-white">
          U
        </div>
      </div>
    </header>
  );
}
