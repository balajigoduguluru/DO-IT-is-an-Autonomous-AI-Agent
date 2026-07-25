const PHASE_MAP: Record<string, string> = {
  UNDERSTAND_GOAL: 'Understanding your request…',
  CONSTRAIN: 'Identifying constraints…',
  PLANNING: 'Planning the best approach…',
  BUILD_DAG: 'Planning…',
  SCHEDULE: 'Organizing the work…',
  RISK_ANALYSIS: 'Checking for possible issues…',
  TOOL_SELECT: 'Choosing the best option…',
  EXECUTE: 'Working on your request…',
  EVALUATE: 'Checking the results…',
  REPLAN: 'Found a better approach…',
  APPROVAL: 'Waiting for your input…',
  SUMMARY: 'Generating final answer…',
  MEMORY_STORE: 'Learning from this task…',
  END: 'Done',
};

const TASK_ACTION_MAP: Record<string, Record<string, string>> = {
  running: {
    supervisor: 'Supervising execution…',
    planner: 'Planning next steps…',
    worker: 'Working…',
    evaluator: 'Evaluating quality…',
    default: 'Processing…',
  },
  completed: {
    flight: 'Flights found ✓',
    hotel: 'Hotels found ✓',
    train: 'Train schedules found ✓',
    weather: 'Weather checked ✓',
    budget: 'Budget calculated ✓',
    email: 'Email ready ✓',
    supervisor: 'Execution supervised ✓',
    planner: 'Plan created ✓',
    worker: 'Task complete ✓',
    evaluator: 'Quality check passed ✓',
    default: 'Completed ✓',
  },
};

export function translatePhase(phase: string): string {
  return PHASE_MAP[phase] ?? 'Working…';
}

export function translateCurrentTask(taskType: string, status: string): string {
  const statusMap = status === 'running' ? TASK_ACTION_MAP.running : TASK_ACTION_MAP.completed;
  const lowerType = taskType.toLowerCase();
  // Check for tool names like "flight_tool", "hotel_tool"
  for (const [key, value] of Object.entries(statusMap)) {
    if (lowerType.includes(key)) return value;
  }
  return statusMap.default;
}

export function translateTaskToActivity(taskType: string, status: string): string | null {
  if (status === 'running') return null; // Don't add activity for running, only completed
  const lowerType = taskType.toLowerCase();
  const activityMap: Record<string, Record<string, string>> = {
    completed: {
      flight: 'Found flights',
      hotel: 'Found hotels',
      train: 'Train schedules checked',
      weather: 'Weather checked',
      budget: 'Budget calculated',
      email: 'Email prepared',
      supervisor: 'Execution verified',
      planner: 'Plan created',
      evaluator: 'Quality verified',
      worker: 'Task done',
    },
    failed: {
      flight: 'Flight search failed — trying alternatives…',
      hotel: 'Hotel search failed — trying alternatives…',
      default: 'Something went wrong, retrying…',
    },
  };
  const map = status === 'failed' ? activityMap.failed : activityMap.completed;
  for (const [key, value] of Object.entries(map)) {
    if (lowerType.includes(key)) return value;
  }
  return status === 'failed' ? activityMap.failed.default : 'Completed';
}

export function translateError(error: string, recoverable: boolean): string {
  if (recoverable) {
    if (error.toLowerCase().includes('timeout')) return 'Something went wrong. Retrying…';
    if (error.toLowerCase().includes('rate')) return 'Too many requests. Slowing down…';
    return 'Something went wrong. Retrying…';
  }
  return 'I wasn\'t able to complete this. Please try again.';
}

export function translateApprovalAction(action: string): string {
  return action || 'proceed with the next step';
}
