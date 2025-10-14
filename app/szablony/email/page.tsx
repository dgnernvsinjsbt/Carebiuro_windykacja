import Link from 'next/link';
import Sidebar from '@/components/Sidebar';
import { TemplateService } from '@/lib/templates/template-service';

export const dynamic = 'force-dynamic';

export default async function EmailTemplatesPage() {
  const templates = await TemplateService.getTemplatesByChannel('email');

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
                className="border-teal-600 text-teal-600 whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm"
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
                className="border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm"
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
          {templates.length === 0 ? (
            <div className="bg-white rounded-lg shadow p-12 text-center">
              <svg
                className="mx-auto h-12 w-12 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                />
              </svg>
              <h3 className="mt-2 text-sm font-medium text-gray-900">Brak szablonów</h3>
              <p className="mt-1 text-sm text-gray-500">Nie znaleziono szablonów e-mail.</p>
            </div>
          ) : (
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {templates.map((template) => (
                <Link
                  key={template.id}
                  href={`/szablony/email/${template.id}`}
                  className="bg-white rounded-lg shadow hover:shadow-md transition-shadow p-6"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">{template.name}</h3>
                      <p className="text-xs text-gray-500 mt-1">Klucz: {template.template_key}</p>
                    </div>
                    <svg
                      className="h-5 w-5 text-gray-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
                      />
                    </svg>
                  </div>

                  {/* Subject */}
                  {template.subject && (
                    <div className="mb-3">
                      <p className="text-xs font-medium text-gray-500 mb-1">Temat:</p>
                      <p className="text-sm text-gray-900 line-clamp-1">{template.subject}</p>
                    </div>
                  )}

                  {/* Body preview */}
                  {template.body_text && (
                    <div className="mb-3">
                      <p className="text-xs font-medium text-gray-500 mb-1">Treść:</p>
                      <p className="text-sm text-gray-600 line-clamp-2">{template.body_text}</p>
                    </div>
                  )}

                  {/* Footer */}
                  <div className="flex items-center justify-between pt-3 border-t border-gray-200 text-xs text-gray-500">
                    <span>{template.placeholders.length} zmiennych</span>
                    <span>{new Date(template.updated_at).toLocaleDateString('pl-PL')}</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
