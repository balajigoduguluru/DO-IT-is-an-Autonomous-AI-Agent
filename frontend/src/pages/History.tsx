import { WorkspaceLayout } from '../layouts/WorkspaceLayout';
import { History as HistoryIcon, Clock } from 'lucide-react';
import { useHistory } from '../hooks/useHistory';

export default function History() {
  const { history, clearHistory } = useHistory();
  return (
    <WorkspaceLayout>
      <div className="flex flex-col h-full max-w-4xl mx-auto w-full pt-12">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <HistoryIcon className="w-8 h-8 text-do-text-secondary" />
            Mission History
          </h1>
          {history.length > 0 && (
            <button 
              onClick={clearHistory}
              className="text-sm font-medium text-red-500 hover:bg-red-500/10 px-4 py-2 rounded-do-sm transition-colors"
            >
              Clear History
            </button>
          )}
        </div>
        
        {history.length === 0 ? (
          <div className="flex-1 bg-do-bg-secondary rounded-do-radius-lg border border-do-bg-tertiary flex items-center justify-center text-do-text-secondary">
            <p>No past missions found. Start executing to build history.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {history.map(item => (
              <div key={item.id} className="bg-do-bg-secondary rounded-do-radius-lg border border-do-bg-tertiary p-6 flex flex-col gap-2">
                <h3 className="font-semibold text-lg text-do-text-primary">{item.title}</h3>
                <div className="flex items-center gap-2 text-sm text-do-text-secondary">
                  <Clock size={14} />
                  <span>{new Date(item.timestamp).toLocaleString()}</span>
                  <span className="opacity-50">•</span>
                  <span>{item.desc}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </WorkspaceLayout>
  );
}
