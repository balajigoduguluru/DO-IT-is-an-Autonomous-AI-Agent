import { WorkspaceLayout } from '../layouts/WorkspaceLayout';
import { Settings as SettingsIcon } from 'lucide-react';

export default function Settings() {
  return (
    <WorkspaceLayout>
      <div className="flex flex-col h-full max-w-2xl mx-auto w-full pt-12">
        <h1 className="text-3xl font-bold mb-8 flex items-center gap-3">
          <SettingsIcon className="w-8 h-8 text-do-text-secondary" />
          Settings
        </h1>
        <div className="space-y-8">
          <section>
            <h2 className="text-xl font-semibold mb-4 border-b border-do-bg-tertiary pb-2">API Configuration</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">OpenAI API Key</label>
                <input type="password" placeholder="sk-..." className="w-full bg-do-bg-secondary border border-do-bg-tertiary rounded-do-radius-sm px-4 py-2 focus:outline-none focus:border-do-active focus:ring-1 focus:ring-do-active transition-all" />
              </div>
            </div>
          </section>
        </div>
      </div>
    </WorkspaceLayout>
  );
}
