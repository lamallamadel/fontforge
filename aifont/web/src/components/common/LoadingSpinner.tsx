interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  label?: string;
}

const sizeMap = { sm: 'h-5 w-5', md: 'h-8 w-8', lg: 'h-12 w-12' };

export function LoadingSpinner({ size = 'md', label = 'Loading…' }: LoadingSpinnerProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3" role="status">
      <span
        className={[
          sizeMap[size],
          'animate-spin rounded-full border-2 border-gray-600 border-t-indigo-500',
        ].join(' ')}
      />
      <span className="sr-only">{label}</span>
    </div>
  );
}
