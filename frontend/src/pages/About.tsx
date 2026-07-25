import { WorkspaceLayout } from '../layouts/WorkspaceLayout';
import { Info } from 'lucide-react';

export default function About() {
  return (
    <WorkspaceLayout>
      <div className="flex flex-col h-full max-w-3xl mx-auto w-full pt-12">
        <h1 className="text-3xl font-bold mb-8 flex items-center gap-3">
          <Info className="w-8 h-8 text-do-text-secondary" />
          About DO IT
        </h1>
        <div className="prose prose-invert max-w-none text-do-text-secondary">
          <p className="text-lg leading-relaxed mb-6">
            DO IT is an autonomous AI agent designed to execute complex digital workflows. 
            By marrying cutting-edge planning models with a secure execution engine, it provides 
            a seamless bridge between human intent and machine action.
          </p>
          <p className="text-lg leading-relaxed">
            Built with production-ready architecture, strict security gates, and a relentless focus 
            on user experience, DO IT acts as the ultimate mission control for your digital life.
          </p>
        </div>
      </div>
    </WorkspaceLayout>
  );
}
