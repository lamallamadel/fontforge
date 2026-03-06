import { useState, useCallback } from 'react';
import { agentApi } from '../api/client';
import type { AgentRunRequest, AgentRunResponse, PromptHistoryItem } from '../api/types';
import { useProjectStore } from '../store/projectStore';

export function useAgent() {
  const { addPromptHistory, promptHistory } = useProjectStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<AgentRunResponse | null>(null);

  const runAgent = useCallback(
    async (request: AgentRunRequest): Promise<AgentRunResponse | null> => {
      setLoading(true);
      setError(null);
      try {
        const result = await agentApi.runAgent(request);
        setLastResult(result);
        const historyItem: PromptHistoryItem = {
          id: result.id,
          prompt: request.prompt,
          response: result,
          timestamp: new Date().toISOString(),
        };
        addPromptHistory(historyItem);
        return result;
      } catch (e) {
        setError('Agent request failed');
        return null;
      } finally {
        setLoading(false);
      }
    },
    [addPromptHistory]
  );

  return {
    loading,
    error,
    lastResult,
    history: promptHistory,
    runAgent,
  };
}
