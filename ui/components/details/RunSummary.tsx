'use client';

import { useState, useEffect, useRef } from 'react';
import { Agent, Run } from '@/types';

const COPY_RESET_DELAY_MS: number = 1_000;

interface RunSummaryProps {
  run: Run;
  agents: Agent[];
  completedTurns: number;
}

export default function RunSummary({ run, agents, completedTurns }: RunSummaryProps) {
  const [copied, setCopied] = useState(false);
  const copyResetTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (copyResetTimerRef.current) {
        clearTimeout(copyResetTimerRef.current);
      }
    };
  }, [run.runId]);

  const handleCopyRunId = async (): Promise<void> => {
      try {
        await navigator.clipboard.writeText(run.runId)
        setCopied(true)
        if (copyResetTimerRef.current) clearTimeout(copyResetTimerRef.current);
        copyResetTimerRef.current = setTimeout(() => setCopied(false), COPY_RESET_DELAY_MS);
      } catch (error) {
        console.log(error instanceof Error ? error.message : 'Copy failed');
        setCopied(false)
      }
  };

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-xl font-semibold text-beige-900">Run Summary</h2>
      <div className="bg-white border border-beige-300 rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-beige-100">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-beige-900">
                Metric
              </th>
              <th className="px-4 py-3 text-left text-sm font-medium text-beige-900">
                Value
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-beige-200">
            <tr>
              <td className="px-4 py-3 text-sm text-beige-800">Run ID</td>
              <td className="px-4 py-3 text-sm text-beige-900 font-mono">
                <div className="flex items-center gap-2">
                  {run.runId}
                  <button 
                    type="button"
                    className="text-accent hover:text-accent-hover cursor-pointer w-12 text-left" 
                    onClick={handleCopyRunId}
                  >
                    {copied ? 'Copied!' : 'Copy'}
                  </button>
                </div>
              </td>
            </tr>
            <tr>
              <td className="px-4 py-3 text-sm text-beige-800">Completed Turns</td>
              <td className="px-4 py-3 text-sm text-beige-900">
                {completedTurns} / {run.totalTurns}
              </td>
            </tr>
            <tr>
              <td className="px-4 py-3 text-sm text-beige-800">Total Agents</td>
              <td className="px-4 py-3 text-sm text-beige-900">
                {run.totalAgents}
              </td>
            </tr>
            <tr>
              <td className="px-4 py-3 text-sm text-beige-800">Status</td>
              <td className="px-4 py-3 text-sm text-beige-900 capitalize">
                {run.status}
              </td>
            </tr>
            <tr>
              <td className="px-4 py-3 text-sm text-beige-800">Created At</td>
              <td className="px-4 py-3 text-sm text-beige-900">
                {new Date(run.createdAt).toLocaleString()}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div>
        <h3 className="text-lg font-medium text-beige-900 mb-3">Agents</h3>
        <div className="space-y-2">
          {agents.map((agent) => (
            <div
              key={agent.handle}
              className="bg-white border border-beige-300 rounded-lg p-4"
            >
              <div className="font-medium text-beige-900">{agent.name}</div>
              <div className="text-sm text-beige-600">{agent.handle}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
