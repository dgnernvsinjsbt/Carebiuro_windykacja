import { notFound } from 'next/navigation';
import Link from 'next/link';
import Sidebar from '@/components/Sidebar';
import { TemplateService } from '@/lib/templates/template-service';
import { WhatsAppEditor } from '@/components/templates/editors/WhatsAppEditor';

interface PageProps {
  params: Promise<{ id: string }>;
}

export const dynamic = 'force-dynamic';

export default async function EditWhatsAppTemplatePage({ params }: PageProps) {
  const { id } = await params;

  const template = await TemplateService.getTemplateById(id);

  if (!template || template.channel !== 'whatsapp') {
    notFound();
  }

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
              <Link
                href="/szablony/email"
                className="border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm"
              >
                E-mail
              </Link>
              <Link
                href="/szablony/sms"
                className="border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm"
              >
                SMS
              </Link>
              <Link
                href="/szablony/whatsapp"
                className="border-teal-600 text-teal-600 whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm"
              >
                WhatsApp
              </Link>
              <Link
                href="/szablony/list-polecony"
                className="border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm"
              >
                List polecony
              </Link>
            </nav>
          </div>

          {/* Content */}
          <div className="space-y-6">
            <WhatsAppEditor template={template} />
          </div>
        </div>
      </main>
    </div>
  );
}
