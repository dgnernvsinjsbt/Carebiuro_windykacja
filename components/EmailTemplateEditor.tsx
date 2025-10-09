'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

interface Template {
  id: string;
  name: string;
  subject: string;
  body_html: string;
  body_text: string;
  body_plain: string;
  placeholders: string[];
}

interface EmailTemplateEditorProps {
  template: Template;
}

export default function EmailTemplateEditor({ template }: EmailTemplateEditorProps) {
  const router = useRouter();
  const [subject, setSubject] = useState(template.subject);
  const [bodyPlain, setBodyPlain] = useState(template.body_plain || template.body_text);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    setSaving(true);
    setError(null);

    try {
      const response = await fetch('/api/email-templates/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: template.id,
          subject,
          body_plain: bodyPlain,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to save template');
      }

      router.push('/settings/email-templates');
      router.refresh();
    } catch (err: any) {
      setError(err.message);
      setSaving(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <button
          onClick={() => router.back()}
          className="text-teal-600 hover:text-teal-700 flex items-center gap-2 mb-4"
        >
          ← Powrót
        </button>
        <h1 className="text-3xl font-bold text-gray-900">Edytuj szablon</h1>
        <p className="text-gray-600 mt-2">{template.name}</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">Błąd zapisu: {error}</p>
        </div>
      )}

      <div className="bg-white p-6 rounded-lg shadow space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Temat e-maila
          </label>
          <input
            type="text"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent"
            placeholder="Przypomnienie o płatności faktury {{invoice_number}}"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Treść wiadomości
          </label>
          <textarea
            value={bodyPlain}
            onChange={(e) => setBodyPlain(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent"
            rows={12}
            placeholder="Dzień dobry {{client_name}},

Uprzejmie przypominamy o płatności za fakturę {{invoice_number}} na kwotę {{amount}}.

Termin płatności: {{due_date}}

Prosimy o jak najszybszą regulację należności.

Pozdrawiamy,
Carebiuro"
          />
          <p className="text-xs text-gray-500 mt-1">
            Pisz zwykły tekst - automatycznie przekonwertujemy go na profesjonalny HTML email
          </p>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="font-medium text-blue-900 mb-2">Dostępne zmienne:</h3>
          <div className="grid grid-cols-2 gap-2 text-sm">
            {template.placeholders?.map((placeholder) => (
              <code key={placeholder} className="px-2 py-1 bg-white rounded text-blue-700">
                {placeholder}
              </code>
            ))}
          </div>
          <p className="text-xs text-blue-700 mt-3">
            Zmienne zostaną automatycznie zamienione na dane z faktury podczas wysyłki
          </p>
        </div>

        <div className="flex gap-4 pt-4">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-6 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? 'Zapisuję...' : 'Zapisz zmiany'}
          </button>
          <button
            onClick={() => router.back()}
            disabled={saving}
            className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors disabled:opacity-50"
          >
            Anuluj
          </button>
        </div>
      </div>
    </div>
  );
}
