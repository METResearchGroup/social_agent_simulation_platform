'use client';

import ConfigForm from '@/components/form/ConfigForm';
import { RunConfig } from '@/types';

interface StartViewProps {
  onSubmit: (config: RunConfig) => void;
  defaultConfig: RunConfig;
}

export default function StartView({ onSubmit, defaultConfig }: StartViewProps) {
  return <ConfigForm onSubmit={onSubmit} defaultConfig={defaultConfig} />;
}
