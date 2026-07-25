import type { BackendStatus } from '../types';

interface Props {
  backendStatus: BackendStatus;
  devMode: boolean;
  onToggleDevMode: () => void;
}

export default function StatusCard({ backendStatus, devMode, onToggleDevMode }: Props) {
  const isOnline = backendStatus === 'online';

  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className="text-lg font-semibold text-gray-900">AI Ready</span>
        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-green-50 border border-green-200">
          <span className={`h-2 w-2 rounded-full ${isOnline ? 'bg-green-500' : 'bg-red-500'} ${isOnline ? '' : 'animate-pulse'}`} />
          <span className="text-xs font-medium text-green-700">
            {isOnline ? 'Connected' : 'Offline'}
          </span>
        </div>
      </div>
      <button
        onClick={onToggleDevMode}
        className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
          devMode
            ? 'bg-primary/10 border-primary/30 text-primary'
            : 'bg-gray-50 border-gray-200 text-gray-400 hover:text-gray-600'
        }`}
      >
        ⚙ Dev Mode
      </button>
    </div>
  );
}
