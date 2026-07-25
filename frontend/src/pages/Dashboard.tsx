import { useExecutionContext } from '../context/ExecutionContext';
import { WorkspaceLayout } from '../layouts/WorkspaceLayout';
import { LandingView } from '../components/workspace/LandingView';
import { ExecutionWorkspace } from '../components/workspace/ExecutionWorkspace';
import ProgressTracker from '../components/workspace/ProgressTracker';
import ActivityTimeline from '../components/workspace/ActivityTimeline';
import { createPortal } from 'react-dom';

export default function Dashboard() {
  const { state } = useExecutionContext();

  const isExecuting = state.status !== 'idle' && state.status !== 'completed' && state.status !== 'failed';
  const hasFinished = state.status === 'completed' || state.status === 'failed';

  const timelinePortalEl = document.getElementById('timeline-portal');

  return (
    <WorkspaceLayout>
      <ProgressTracker 
        progress={state.progress} 
        visible={isExecuting} 
      />

      <LandingView />
      <ExecutionWorkspace />

      {/* Render ActivityTimeline into the portal provided by WorkspaceLayout if it exists */}
      {timelinePortalEl && createPortal(
        <ActivityTimeline 
          activities={state.activities} 
          visible={isExecuting || hasFinished} 
        />,
        timelinePortalEl
      )}
    </WorkspaceLayout>
  );
}
