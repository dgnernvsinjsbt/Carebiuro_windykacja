'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import type { MessageTemplate } from '@/lib/templates/types';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Save, X } from 'lucide-react';

interface WhatsAppEditorProps {
  template: MessageTemplate;
}

export function WhatsAppEditor({ template }: WhatsAppEditorProps) {
  const router = useRouter();
  const [bodyText, setBodyText] = useState(template.body_text || '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const charCount = bodyText.length;

  async function handleSave() {
    setSaving(true);
    setError(null);

    try {
      const response = await fetch('/api/templates/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: template.id,
          channel: 'whatsapp',
          body_text: bodyText,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to save template');
      }

      router.push('/szablony/whatsapp');
      router.refresh();
    } catch (err: any) {
      setError(err.message);
      setSaving(false);
    }
  }

  return (
    <div className="max-w-4xl space-y-6">
      {/* Error message */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Editor */}
        <div className="space-y-6">
          <Card>
            <CardContent className="pt-6 space-y-4">
              {/* Body field */}
              <div className="space-y-2">
                <Label htmlFor="body">Treść wiadomości WhatsApp</Label>
                <Textarea
                  id="body"
                  value={bodyText}
                  onChange={(e) => setBodyText(e.target.value)}
                  rows={12}
                  className="font-sans text-sm"
                  placeholder={`Dzień dobry! 👋

Uprzejmie przypominamy o nieopłaconej fakturze:

📄 Numer: {{numer_faktury}}
💰 Kwota: {{kwota}} {{waluta}}
📅 Termin: {{termin}}

Prosimy o pilną realizację płatności.

W razie pytań, jesteśmy do dyspozycji.

Pozdrawiamy,
Carebiuro`}
                />
                <p className="text-xs text-muted-foreground">
                  {charCount} znaków • WhatsApp wspiera emotikony i formatowanie
                </p>
              </div>

              {/* Placeholders reference */}
              <Card className="bg-blue-50 border-blue-200">
                <CardContent className="pt-4">
                  <h3 className="font-medium text-blue-900 text-sm mb-2">
                    Dostępne zmienne:
                  </h3>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    {template.placeholders.map((placeholder) => (
                      <code
                        key={placeholder.key}
                        className="px-2 py-1 bg-white rounded text-blue-700 border border-blue-200 text-xs"
                      >
                        {placeholder.key}
                      </code>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Info box */}
              <div className="bg-muted p-3 rounded-md text-sm space-y-1">
                <p className="font-medium">Wskazówki:</p>
                <ul className="text-xs text-muted-foreground space-y-0.5">
                  <li>• Używaj emotikon aby wiadomość była bardziej przyjazna</li>
                  <li>• WhatsApp nie ma limitu znaków jak SMS</li>
                  <li>• Zachowaj profesjonalny ton mimo nieformalnego kanału</li>
                </ul>
              </div>

              {/* Action buttons */}
              <div className="flex gap-4 pt-4">
                <Button onClick={handleSave} disabled={saving} className="gap-2">
                  <Save className="h-4 w-4" />
                  {saving ? 'Zapisuję...' : 'Zapisz zmiany'}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => router.back()}
                  disabled={saving}
                  className="gap-2"
                >
                  <X className="h-4 w-4" />
                  Anuluj
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Preview */}
        <div>
          <Card>
            <CardContent className="pt-6">
              <h3 className="font-medium mb-4">Podgląd wiadomości</h3>

              {/* WhatsApp mockup */}
              <div className="bg-[#128C7E] rounded-2xl p-4 max-w-sm mx-auto">
                <div className="bg-[#DCF8C6] rounded-lg rounded-br-none p-3 shadow-sm min-h-[200px]">
                  <div className="text-sm text-gray-900 whitespace-pre-wrap">
                    {bodyText || (
                      <span className="text-gray-500 italic">
                        Wpisz treść wiadomości...
                      </span>
                    )}
                  </div>
                  <div className="flex justify-end items-center gap-1 text-xs text-gray-600 mt-2">
                    <span>Teraz</span>
                    <span>✓✓</span>
                  </div>
                </div>
              </div>

              {/* Preview info */}
              <div className="mt-4 text-xs text-muted-foreground">
                <p>
                  Wiadomość wyśle się przez integrację WhatsApp Business API
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
