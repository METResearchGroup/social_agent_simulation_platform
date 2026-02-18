'use client';

import { Agent, Run } from '@/types';

interface RunSummaryProps {
  run: Run;
  agents: Agent[];
  completedTurns: number;
}

export default function RunSummary({ run, agents, completedTurns }: RunSummaryProps) {
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
                {run.runId}
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
