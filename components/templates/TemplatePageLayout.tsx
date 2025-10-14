import Link from 'next/link';
import Sidebar from '../Sidebar';

interface TemplatePageLayoutProps {
  children: React.ReactNode;
  activeTab: 'email' | 'sms' | 'whatsapp' | 'list-polecony';
}

export function TemplatePageLayout({ children, activeTab }: TemplatePageLayoutProps) {
  const tabs = [
    { key: 'email', label: 'E-mail', href: '/szablony/email' },
    { key: 'sms', label: 'SMS', href: '/szablony/sms' },
    { key: 'whatsapp', label: 'WhatsApp', href: '/szablony/whatsapp' },
    { key: 'list-polecony', label: 'List polecony', href: '/szablony/list-polecony' },
  ];

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <main className="flex-1 p-8">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-6">
            <h1 className="text-3xl font-bold text-gray-900">Szablony wiadomości</h1>
            <p className="mt-2 text-gray-600">
              Zarządzaj treścią wiadomości wysyłanych do klientów
            </p>
          </div>

          {/* Tabs Navigation */}
          <div className="mb-6 border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              {tabs.map((tab) => (
                <Link
                  key={tab.key}
                  href={tab.href}
                  className={
                    tab.key === activeTab
                      ? 'border-teal-600 text-teal-600 whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm'
                  }
                >
                  {tab.label}
                </Link>
              ))}
            </nav>
          </div>

          {/* Content */}
          {children}
        </div>
      </main>
    </div>
  );
}
