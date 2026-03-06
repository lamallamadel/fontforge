import { Link } from 'react-router-dom';

export function NotFound() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-6 p-6 text-center">
      <div className="text-8xl font-bold text-gray-800">404</div>
      <div>
        <h1 className="text-2xl font-bold text-white">Page Not Found</h1>
        <p className="mt-2 text-gray-400">The page you're looking for doesn't exist.</p>
      </div>
      <Link
        to="/"
        className="rounded-lg bg-indigo-600 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-indigo-500"
      >
        Back to Dashboard
      </Link>
    </div>
  );
}
