import { useMemo } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  ConnectionMode,
  MarkerType,
  Position,
  Handle,
  NodeProps,
} from 'reactflow';
import 'reactflow/dist/style.css';

export interface TaskNode {
  id: string;
  label: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'replanning';
  type?: string;
  metadata?: Record<string, unknown>;
}

export interface TaskEdge {
  from: string;
  to: string;
  label?: string;
}

interface DAGViewProps {
  nodes?: TaskNode[];
  edges?: TaskEdge[];
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
}

const statusColors: Record<string, string> = {
  pending: 'node-pending',
  running: 'node-running',
  completed: 'node-completed',
  failed: 'node-failed',
  replanning: 'node-replanning',
};

const statusLabels: Record<string, string> = {
  pending: 'Pending',
  running: 'Running',
  completed: 'Completed',
  failed: 'Failed',
  replanning: 'Replanning',
};

function TaskNodeComponent({ data }: NodeProps) {
  const status = data.status as string;
  const statusClass = statusColors[status] || 'node-pending';

  return (
    <div
      className={`min-w-[160px] rounded-xl border-2 px-4 py-3 ${statusClass} bg-gray-900 text-gray-100 shadow-lg transition-all duration-200`}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-gray-500 !border-2 !border-gray-700"
      />
      <div className="flex items-center gap-2">
        <span className="node-status-dot h-2.5 w-2.5 rounded-full" />
        <span className="text-sm font-medium leading-tight">{data.label}</span>
      </div>
      <div className="mt-1.5">
        <span
          className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${
            status === 'running'
              ? 'badge-running'
              : status === 'completed'
                ? 'badge-completed'
                : status === 'failed'
                  ? 'badge-failed'
                  : status === 'replanning'
                    ? 'badge-replanning'
                    : 'badge-pending'
          }`}
        >
          {statusLabels[status] || status}
        </span>
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-gray-500 !border-2 !border-gray-700"
      />
    </div>
  );
}

const nodeTypes = { taskNode: TaskNodeComponent };

export default function DAGView({
  nodes: taskNodes,
  edges: taskEdges,
  loading = false,
  error = null,
  onRetry,
}: DAGViewProps) {
  const flowNodes: Node[] = useMemo(() => {
    if (!taskNodes) return [];
    return taskNodes.map((n, idx) => ({
      id: n.id,
      type: 'taskNode',
      position: { x: 0, y: idx * 120 },
      data: { label: n.label, status: n.status, metadata: n.metadata },
    }));
  }, [taskNodes]);

  const flowEdges: Edge[] = useMemo(() => {
    if (!taskEdges) return [];
    return taskEdges.map((e) => ({
      id: `${e.from}->${e.to}`,
      source: e.from,
      target: e.to,
      label: e.label,
      animated: true,
      style: { stroke: '#6b7280', strokeWidth: 2 },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: '#6b7280',
      },
      labelStyle: { fill: '#9ca3af', fontSize: 11 },
    }));
  }, [taskEdges]);

  // Layout can be enhanced with dagre if desired.

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="skeleton h-64 w-full max-w-lg rounded-xl" />
          <p className="text-sm text-gray-500">Loading graph...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-4 rounded-xl border border-red-500/30 bg-red-500/10 px-8 py-6 text-center">
          <svg
            className="h-10 w-10 text-red-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
            />
          </svg>
          <p className="text-sm text-red-300">{error}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="rounded-lg bg-red-500/20 px-4 py-2 text-sm font-medium text-red-300 transition-colors hover:bg-red-500/30"
            >
              Retry
            </button>
          )}
        </div>
      </div>
    );
  }

  if (!taskNodes || taskNodes.length === 0) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-gray-700 px-8 py-12 text-center">
          <svg
            className="h-10 w-10 text-gray-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5m.75-9l3-3 2.148 2.148A12.061 12.061 0 0116.5 7.605"
            />
          </svg>
          <p className="text-sm text-gray-500">No tasks yet</p>
          <p className="text-xs text-gray-600">
            Set a goal and start execution to see the task graph.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full">
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        nodeTypes={nodeTypes}
        connectionMode={ConnectionMode.Loose}
        fitView
        attributionPosition="bottom-left"
        minZoom={0.2}
        maxZoom={3}
        defaultEdgeOptions={{
          animated: true,
          style: { stroke: '#6b7280', strokeWidth: 2 },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: '#6b7280',
          },
        }}
      >
        <Background color="#374151" gap={20} size={1} />
        <Controls
          className="!border-gray-700 !bg-gray-900 !text-gray-300"
          showInteractive={false}
        />
        <MiniMap
          nodeColor={(node: any) => {
            const status = node.data?.status as string;
            switch (status) {
              case 'running':
                return '#3b82f6';
              case 'completed':
                return '#22c55e';
              case 'failed':
                return '#ef4444';
              case 'replanning':
                return '#eab308';
              default:
                return '#6b7280';
            }
          }}
          maskColor="rgba(3, 7, 18, 0.7)"
          className="!border-gray-700"
        />
      </ReactFlow>
    </div>
  );
}
