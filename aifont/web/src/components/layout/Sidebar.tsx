import { NavLink, useParams } from 'react-router-dom';

interface NavItem {
  label: string;
  icon: React.ReactNode;
  to: string;
}

export function Sidebar() {
  const { projectId } = useParams<{ projectId: string }>();

  const topItems: NavItem[] = [
    {
      label: 'Dashboard',
      to: '/',
      icon: (
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
        </svg>
      ),
    },
  ];

  const projectItems: NavItem[] = projectId
    ? [
        {
          label: 'Studio',
          to: `/studio/${projectId}`,
          icon: (
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
            </svg>
          ),
        },
        {
          label: 'AI Prompt',
          to: `/studio/${projectId}/prompt`,
          icon: (
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          ),
        },
        {
          label: 'Preview',
          to: `/studio/${projectId}/preview`,
          icon: (
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
          ),
        },
        {
          label: 'Export',
          to: `/studio/${projectId}/export`,
          icon: (
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
          ),
        },
      ]
    : [];

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    [
      'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
      isActive
        ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
        : 'text-gray-400 hover:bg-gray-800 hover:text-white',
    ].join(' ');

  return (
    <aside className="flex w-16 flex-col items-center border-r border-gray-800 bg-gray-950 py-4 lg:w-56 lg:items-stretch lg:px-3">
      {/* Logo */}
      <div className="mb-6 flex items-center justify-center lg:justify-start lg:px-1">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white font-bold text-sm">
          AI
        </div>
        <span className="ml-2 hidden text-base font-semibold text-white lg:block">
          AIFont Studio
        </span>
      </div>

      {/* Top nav */}
      <nav className="flex flex-col gap-1 w-full">
        {topItems.map((item) => (
          <NavLink key={item.to} to={item.to} end className={navLinkClass}>
            <span className="flex-shrink-0">{item.icon}</span>
            <span className="hidden lg:block">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Project nav */}
      {projectItems.length > 0 && (
        <>
          <div className="my-3 hidden border-t border-gray-800 lg:block" />
          <p className="mb-1 hidden px-1 text-xs font-semibold uppercase tracking-wider text-gray-500 lg:block">
            Project
          </p>
          <nav className="flex flex-col gap-1 w-full">
            {projectItems.map((item) => (
              <NavLink key={item.to} to={item.to} end className={navLinkClass}>
                <span className="flex-shrink-0">{item.icon}</span>
                <span className="hidden lg:block">{item.label}</span>
              </NavLink>
            ))}
          </nav>
        </>
      )}
    </aside>
  );
}
