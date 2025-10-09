import { supabaseAdmin } from '@/lib/supabase';
import Sidebar from '@/components/Sidebar';
import Link from 'next/link';

export const revalidate = 60;

export default async function EmailTemplatesPage() {
  const { data: templates, error } = await supabaseAdmin()
    .from('email_templates')
    .select('*')
    .order('id');

  if (error) {
    console.error('[EmailTemplates] Error loading templates:', error);
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <main className="flex-1 p-8">
        <div className="max-w-5xl mx-auto">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Szablony E-maili</h1>
          <p className="text-gray-600 mb-8">
            Zarządzaj treścią e-maili wysyłanych do klientów jako przypomnienia o płatnościach.
          </p>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
              <p className="text-red-800">
                Błąd ładowania szablonów: {error.message}
              </p>
              <p className="text-sm text-red-600 mt-2">
                Upewnij się, że tabela email_templates istnieje w Supabase.
              </p>
            </div>
          )}

          <div className="grid gap-4">
            {templates?.map((template) => (
              <div key={template.id} className="bg-white p-6 rounded-lg shadow hover:shadow-md transition-shadow">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="font-bold text-lg text-gray-900">
                        {template.name}
                      </h3>
                      <span className="px-2 py-1 text-xs font-mono bg-gray-100 text-gray-700 rounded">
                        {template.id}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mb-1">
                      <strong>Temat:</strong> {template.subject}
                    </p>
                    <p className="text-xs text-gray-500">
                      Ostatnia aktualizacja: {new Date(template.updated_at).toLocaleString('pl-PL')}
                    </p>
                  </div>
                  <Link
                    href={`/settings/email-templates/${template.id}`}
                    className="px-4 py-2 bg-teal-600 text-white rounded hover:bg-teal-700 transition-colors"
                  >
                    Edytuj
                  </Link>
                </div>
              </div>
            ))}
          </div>

          {templates && templates.length === 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
              <p className="text-yellow-800">
                Brak szablonów. Uruchom migrację SQL aby dodać domyślne szablony.
              </p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
