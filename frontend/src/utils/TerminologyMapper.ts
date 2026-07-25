export const translatePhase = (backendPhase: string): string => {
  const mapping: Record<string, string> = {
    PLANNER_START: 'Understanding your request',
    PLANNING: 'Planning the best approach',
    SCHEDULER_START: 'Organizing tasks',
    SCHEDULING: 'Organizing tasks',
    EXECUTION_START: 'Preparing to work',
    EXECUTING: 'Working',
    RISK_CHECK: 'Verifying safety constraints',
    MEMORY_RETRIEVAL: 'Searching past interactions',
    TOOL_SELECTION: 'Choosing the right tools',
    TOOL_EXECUTION: 'Working',
    COMPARING: 'Comparing available options',
    EVALUATING: 'Evaluating results',
    FINALIZING: 'Preparing your answer',
    COMPLETED: 'Done'
  };

  return mapping[backendPhase.toUpperCase()] || 'Working';
};

export const translateCurrentTask = (task: string): string => {
  // If the task has technical jargon, simplify it
  const lowerTask = task.toLowerCase();
  
  if (lowerTask.includes('dag') || lowerTask.includes('graph')) {
    return 'Planning execution path...';
  }
  if (lowerTask.includes('spawn') || lowerTask.includes('agent')) {
    return 'Assigning task...';
  }
  if (lowerTask.includes('http') || lowerTask.includes('api') || lowerTask.includes('fetch')) {
    return 'Retrieving information...';
  }
  if (lowerTask.includes('parse') || lowerTask.includes('json')) {
    return 'Analyzing data...';
  }
  
  // Return natural language if already natural, or fallback
  return task.trim() ? `${task.charAt(0).toUpperCase()}${task.slice(1)}...` : 'Thinking...';
};

export const translateError = (error: string): string => {
  const lowerError = error.toLowerCase();
  if (lowerError.includes('offline') || lowerError.includes('fetch failed')) {
    return 'Agent unavailable. Please start the backend.';
  }
  if (lowerError.includes('timeout')) {
    return 'The operation took too long. Please try again.';
  }
  return 'I encountered an unexpected issue while working on this.';
};
