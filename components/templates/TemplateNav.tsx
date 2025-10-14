'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';

const tabs = [
  { href: '/szablony/email', label: 'E-mail' },
  { href: '/szablony/sms', label: 'SMS' },
  { href: '/szablony/whatsapp', label: 'WhatsApp' },
  { href: '/szablony/list-polecony', label: 'List polecony' },
];

export function TemplateNav() {
  const pathname = usePathname();

  const isActive = (href: string) => {
    return pathname?.startsWith(href);
  };

  return (
    <div className="border-b border-border">
      <nav className="flex space-x-8" aria-label="Template channels">
        {tabs.map((tab) => (
          <Link
            key={tab.href}
            href={tab.href}
            className={cn(
              'border-b-2 py-4 px-1 text-sm font-medium transition-colors',
              isActive(tab.href)
                ? 'border-primary text-foreground'
                : 'border-transparent text-muted-foreground hover:border-gray-300 hover:text-foreground'
            )}
          >
            {tab.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
