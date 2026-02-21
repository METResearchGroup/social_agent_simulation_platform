'use client';

import PdfUploadCard from '@/components/pdf/PdfUploadCard';
import SignIn from '@/components/auth/SignIn';
import SimulationLayout from '@/components/layout/SimulationLayout';
import { useAuth } from '@/contexts/AuthContext';

export default function PdfUploadPage() {
  const { user, isLoading: authLoading } = useAuth();

  if (authLoading || !user) {
    return (
      <SimulationLayout>
        <SignIn />
      </SimulationLayout>
    );
  }

  return (
    <SimulationLayout>
      <div className="flex flex-1 items-center justify-center p-6">
        <PdfUploadCard />
      </div>
    </SimulationLayout>
  );
}

