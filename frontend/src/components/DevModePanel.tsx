import { useState } from 'react';
import type { DevModeData } from '../types';
import { formatTimestamp, formatDuration } from '../utils/formatters';

interface Props {
  devData: DevModeData;
  visible: boolean;
}

type DevTab = 'graph' | 'ledger' | 'events' | 'metrics';

export default function DevModePanel({ devData, visible }: Props) {
  const [activeTab, setActiveTab] = useState<DevTab>('graph');

  if (!visible) return null;

  const tabs: { key: DevTab; label: string }[] = [
    { key: 'graph', label: 'Graph' },
    { key: 'ledger', label: 'Ledger' },
    { key: 'events', label: 'Events' },
    { key: 'metrics', label: 'Metrics' },
  ];

  return (
    <div className="bg-white rounded-xl border border-amber-200 shadow-sm overflow-hidden">
      <div className="bg-amber-50 px-4 py-2 border-b border-amber-200">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-amber-800 uppercase tracking-wider">
            ⚙ Developer Mode
          </span>
          <span className="text-[10px] text-amber-600">
            Session: {devData.sessionId ? devData.sessionId.slice(0, 12) : '—'}
          </span>
          {devData.executionTimeMs && (
            <span className="text-[10px] text-amber-600 ml-auto">
              Time: {formatDuration(devData.executionTimeMs)}
            </span>
          )}
        </div>
      </div>

      {/* Tab navigation */}
      <div className="flex gap-0 border-b border-gray-100 px-2">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-3 py-2 text-xs font-medium transition-colors ${
              activeTab === tab.key
                ? 'text-primary border-b-2 border-primary'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="p-4 max-h-80 overflow-y-auto text-xs font-mono">
        {activeTab === 'graph' && (
          <div className="space-y-2">
            <div className="text-gray-400 mb-2">
              Nodes: {Object.keys(devData.graphNodes).length} | Edges: {devData.graphEdges.length}
            </div>
            {Object.entries(devData.graphNodes).slice(0, 20).map(([id, node]) => (
              <div key={id} className="flex items-center gap-2 text-gray-600">
                <span className="text-gray-400">{id.slice(0, 12)}</span>
                <span className="text-gray-300">|</span>
                <span className="text-gray-800">{(node as Record<string, string>)?.agent_type ?? '?'}</span>
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                  (node as Record<string, string>)?.status === 'COMPLETED' ? 'bg-green-100 text-green-700' :
                  (node as Record<string, string>)?.status === 'RUNNING' ? 'bg-blue-100 text-blue-700' :
                  (node as Record<string, string>)?.status === 'FAILED' ? 'bg-red-100 text-red-700' :
                  'bg-gray-100 text-gray-600'
                }`}>
                  {(node as Record<string, string>)?.status ?? 'PENDING'}
                </span>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'ledger' && (
          <div className="space-y-1.5">
            {devData.executionLedger.length === 0 && (
              <span className="text-gray-400">No ledger entries yet</span>
            )}
            {devData.executionLedger.slice(-30).reverse().map((entry, i) => (
              <div key={i} className="flex items-start gap-2 text-gray-600">
                <span className="text-gray-400 flex-shrink-0">
                  {formatTimestamp((entry as Record<string, string>).timestamp ?? '')}
                </span>
                <span className="text-gray-300">|</span>
                <span className="font-medium text-gray-700">{(entry as Record<string, string>).agent ?? '?'}</span>
                <span className="text-gray-500">{(entry as Record<string, string>).action ?? ''}</span>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'events' && (
          <div className="space-y-1.5">
            {devData.websocketEvents.length === 0 && (
              <span className="text-gray-400">No WebSocket events yet</span>
            )}
            {devData.websocketEvents.slice(-20).reverse().map((evt, i) => (
              <div key={i} className="text-gray-600">
                <span className="text-gray-400">{evt.timestamp.slice(11, 19)}</span>
                {' '}
                <span className="text-amber-700 font-medium">{evt.type}</span>
                {' '}
                <span className="text-gray-400">{JSON.stringify(evt.data).slice(0, 80)}</span>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'metrics' && (
          <div className="grid grid-cols-2 gap-3">
            <Metric label="Current Agent" value={devData.currentAgent ?? '—'} />
            <Metric label="Tool Selected" value={devData.toolSelection ?? '—'} />
            <Metric label="LLM Calls" value={String(devData.llmCalls)} />
            <Metric label="Tool Calls" value={String(devData.toolCalls)} />
            <Metric label="Running Tasks" value={String(devData.runningTasks)} />
            <Metric label="Completed" value={String(devData.completedTasks)} />
            <Metric label="Failed" value={String(devData.failedTasks)} />
            <Metric label="Execution Time" value={devData.executionTimeMs ? formatDuration(devData.executionTimeMs) : '—'} />
            <Metric label="API Requests" value={String(devData.apiRequests.length)} />
            <Metric label="Ledger Entries" value={String(devData.executionLedger.length)} />
            <Metric label="WS Events" value={String(devData.websocketEvents.length)} />
          </div>
        )}
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-50 rounded-lg p-2.5">
      <div className="text-[10px] font-medium text-gray-400 uppercase tracking-wider">{label}</div>
      <div className="text-sm font-semibold text-gray-800 mt-0.5">{value}</div>
    </div>
  );
}
