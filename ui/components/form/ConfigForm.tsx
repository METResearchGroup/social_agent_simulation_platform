'use client';

import { useState } from 'react';
import { RunConfig } from '@/types';

interface ConfigFormProps {
  onSubmit: (config: RunConfig) => void;
  defaultConfig: RunConfig;
}

export default function ConfigForm({ onSubmit, defaultConfig }: ConfigFormProps) {
  const [numAgents, setNumAgents] = useState(defaultConfig.numAgents);
  const [numTurns, setNumTurns] = useState(defaultConfig.numTurns);

  const handleSubmit = (event: React.FormEvent): void => {
    event.preventDefault();
    onSubmit({ numAgents, numTurns });
  };

  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="w-full max-w-md">
        <h1 className="text-2xl font-semibold text-beige-900 mb-8 text-center">
          Start New Simulation
        </h1>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label
              htmlFor="numAgents"
              className="block text-sm font-medium text-beige-800 mb-2"
            >
              Number of Agents
            </label>
            <input
              id="numAgents"
              type="number"
              min="1"
              max="20"
              value={numAgents}
              onChange={(event) => {
                const value: number = Number(event.currentTarget.value);
                setNumAgents(Number.isNaN(value) || value < 1 ? 1 : value);
              }}
              className="w-full px-4 py-2 border border-beige-300 rounded-lg bg-white text-beige-900 focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent"
              required
            />
          </div>
          <div>
            <label
              htmlFor="numTurns"
              className="block text-sm font-medium text-beige-800 mb-2"
            >
              Number of Turns
            </label>
            <input
              id="numTurns"
              type="number"
              min="1"
              max="100"
              value={numTurns}
              onChange={(event) => {
                const value: number = Number(event.currentTarget.value);
                setNumTurns(Number.isNaN(value) || value < 1 ? 1 : value);
              }}
              className="w-full px-4 py-2 border border-beige-300 rounded-lg bg-white text-beige-900 focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent"
              required
            />
          </div>
          <button
            type="submit"
            className="w-full px-6 py-3 bg-accent text-white rounded-lg font-medium hover:bg-accent-hover transition-colors"
          >
            Start Simulation
          </button>
        </form>
      </div>
    </div>
  );
}
