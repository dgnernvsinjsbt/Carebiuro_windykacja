'use client';

import { useRouter } from 'next/navigation';

interface BackButtonProps {
  children: React.ReactNode;
  className?: string;
}

export default function BackButton({ children, className = '' }: BackButtonProps) {
  const router = useRouter();

  return (
    <button
      onClick={() => router.back()}
      className={className}
      type="button"
    >
      {children}
    </button>
  );
}
