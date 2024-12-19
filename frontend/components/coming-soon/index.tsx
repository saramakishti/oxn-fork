'use client';
import React from 'react';
import { Button } from '@/components/ui/button';
import { useRouter } from 'next/navigation';
import { Construction } from 'lucide-react';

export default function ComingSoon({ showBackButton = true }: { showBackButton: boolean }) {
  const router = useRouter();

  const handleGoBack = () => {
    router.back();
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-6 bg-background text-foreground">
      <Construction className="w-16 h-16 mb-4" />
      <h1 className="text-4xl font-bold mb-2">Coming Soon</h1>
      <p className="text-lg text-center mb-6">
        This page is under construction.
      </p>
      {showBackButton && <Button variant="default" size="lg" onClick={handleGoBack}>
        Go back
      </Button>}
    </div>
  );
}
