import { useParams } from 'react-router-dom';
import { PromptInput } from '../components/prompt/PromptInput';
import { PromptHistory } from '../components/prompt/PromptHistory';
import { PromptResult } from '../components/prompt/PromptResult';
import { useAgent } from '../hooks/useAgent';
import { useProjectStore } from '../store/projectStore';

export function PromptPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { activeProject } = useProjectStore();
  const { loading, lastResult, history, runAgent } = useAgent();

  const handleSubmit = async (prompt: string) => {
    await runAgent({
      prompt,
      fontId: projectId,
    });
  };

  return (
    <div className="flex h-full flex-col lg:flex-row">
      {/* Main panel */}
      <div className="flex flex-1 flex-col gap-6 overflow-y-auto p-6">
        {/* Page title */}
        <div>
          <h1 className="text-xl font-bold text-white">AI Prompt</h1>
          {activeProject && (
            <p className="mt-0.5 text-sm text-gray-400">
              Generating for <span className="text-white">{activeProject.name}</span>
            </p>
          )}
        </div>

        {/* Input */}
        <PromptInput onSubmit={handleSubmit} loading={loading} />

        {/* Result */}
        <PromptResult
          result={lastResult}
          onApply={() => console.log('Apply result to font')}
        />
      </div>

      {/* History sidebar */}
      <div className="w-full overflow-y-auto border-t border-gray-800 p-4 lg:w-80 lg:border-l lg:border-t-0">
        <h2 className="mb-4 text-sm font-semibold text-gray-400">History</h2>
        <PromptHistory items={history} />
      </div>
    </div>
  );
}
