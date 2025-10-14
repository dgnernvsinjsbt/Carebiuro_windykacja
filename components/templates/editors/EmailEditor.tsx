'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import type { MessageTemplate } from '@/lib/templates/types';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Save, X } from 'lucide-react';

interface EmailEditorProps {
  template: MessageTemplate;
}

export function EmailEditor({ template }: EmailEditorProps) {
  const router = useRouter();
  const [subject, setSubject] = useState(template.subject || '');
  const [bodyText, setBodyText] = useState(template.body_text || '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    setSaving(true);
    setError(null);

    try {
      const response = await fetch('/api/templates/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: template.id,
          channel: 'email',
          subject,
          body_text: bodyText,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to save template');
      }

      router.push('/szablony/email');
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

      <Card>
        <CardContent className="pt-6 space-y-6">
          {/* Subject field */}
          <div className="space-y-2">
            <Label htmlFor="subject">Temat e-maila</Label>
            <Input
              id="subject"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="Przypomnienie o płatności faktury {{numer_faktury}}"
            />
          </div>

          {/* Body field */}
          <div className="space-y-2">
            <Label htmlFor="body">Treść wiadomości</Label>
            <Textarea
              id="body"
              value={bodyText}
              onChange={(e) => setBodyText(e.target.value)}
              rows={12}
              placeholder={`Dzień dobry {{nazwa_klienta}},

Uprzejmie przypominamy o płatności za fakturę {{numer_faktury}} na kwotę {{kwota}}.

Termin płatności: {{termin}}

Prosimy o jak najszybszą regulację należności.

Pozdrawiamy,
Carebiuro`}
            />
            <p className="text-xs text-muted-foreground">
              Pisz zwykły tekst - automatycznie przekonwertujemy go na profesjonalny HTML email
            </p>
          </div>

          {/* Placeholders reference */}
          <Card className="bg-blue-50 border-blue-200">
            <CardContent className="pt-6">
              <h3 className="font-medium text-blue-900 mb-3">Dostępne zmienne:</h3>
              <div className="grid grid-cols-2 gap-2 text-sm">
                {template.placeholders.map((placeholder) => (
                  <code
                    key={placeholder.key}
                    className="px-2 py-1 bg-white rounded text-blue-700 border border-blue-200"
                  >
                    {placeholder.key}
                  </code>
                ))}
              </div>
              <p className="text-xs text-blue-700 mt-3">
                Zmienne zostaną automatycznie zamienione na dane z faktury podczas wysyłki
              </p>
            </CardContent>
          </Card>

          {/* Action buttons */}
          <div className="flex gap-4 pt-4">
            <Button
              onClick={handleSave}
              disabled={saving}
              className="gap-2"
            >
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
  );
}
