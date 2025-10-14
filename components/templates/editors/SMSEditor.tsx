'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import type { MessageTemplate } from '@/lib/templates/types';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Save, X, AlertTriangle } from 'lucide-react';
import { SMSValidator } from '@/lib/templates/validators/sms-validator';
import { cn } from '@/lib/utils';

interface SMSEditorProps {
  template: MessageTemplate;
}

export function SMSEditor({ template }: SMSEditorProps) {
  const router = useRouter();
  const [bodyText, setBodyText] = useState(template.body_text || '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Calculate SMS validation in real-time
  const validator = new SMSValidator(bodyText);
  const validation = validator.validate();

  async function handleSave() {
    // Don't save if invalid
    if (!validation.isValid) {
      setError('Wiadomość jest zbyt długa. Maksymalnie 3 segmenty SMS.');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const response = await fetch('/api/templates/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: template.id,
          channel: 'sms',
          body_text: bodyText,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to save template');
      }

      router.push('/szablony/sms');
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
                <Label htmlFor="body">Treść wiadomości SMS</Label>
                <Textarea
                  id="body"
                  value={bodyText}
                  onChange={(e) => setBodyText(e.target.value)}
                  rows={8}
                  className={cn(
                    'font-mono text-sm',
                    !validation.isValid && 'border-red-500 focus-visible:ring-red-500'
                  )}
                  placeholder="Szanowni Państwo, przypominamy o fakturtze {{numer_faktury}} na kwotę {{kwota}} {{waluta}}..."
                />

                {/* Character counter */}
                <div className="flex items-center justify-between text-sm">
                  <span
                    className={cn(
                      'font-medium',
                      validation.length > validation.maxLength * 0.9 &&
                        'text-orange-600',
                      !validation.isValid && 'text-red-600'
                    )}
                  >
                    {validation.length} / {validation.maxLength} znaków
                  </span>
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <span>
                      {validation.segments}{' '}
                      {validation.segments === 1 ? 'segment' : 'segmenty'}
                    </span>
                    {validation.encoding === 'UCS-2' && (
                      <span className="text-orange-600 text-xs font-medium">
                        (polskie znaki)
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Warnings */}
              {validation.warnings.length > 0 && (
                <Alert>
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>
                    <ul className="list-disc list-inside space-y-1 text-sm">
                      {validation.warnings.map((warning, i) => (
                        <li key={i}>{warning}</li>
                      ))}
                    </ul>
                  </AlertDescription>
                </Alert>
              )}

              {/* Info box */}
              <div className="bg-muted p-3 rounded-md text-sm space-y-1">
                <p className="font-medium">Limity SMS:</p>
                <ul className="text-xs text-muted-foreground space-y-0.5">
                  <li>• Standardowy: 160 znaków (GSM-7)</li>
                  <li>• Z polskimi znakami: 70 znaków (UCS-2)</li>
                  <li>• Maksymalnie: 3 segmenty SMS</li>
                </ul>
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

              {/* Action buttons */}
              <div className="flex gap-4 pt-4">
                <Button
                  onClick={handleSave}
                  disabled={saving || !validation.isValid}
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

        {/* Preview */}
        <div>
          <Card>
            <CardContent className="pt-6">
              <h3 className="font-medium mb-4">Podgląd wiadomości</h3>

              {/* Phone mockup */}
              <div className="bg-gray-100 rounded-2xl p-4 max-w-sm mx-auto">
                <div className="bg-white rounded-lg p-4 shadow-sm min-h-[200px]">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                      <span className="font-medium">Carebiuro</span>
                      <span>•</span>
                      <span>SMS</span>
                    </div>
                    <div className="text-sm text-gray-900 whitespace-pre-wrap">
                      {bodyText || (
                        <span className="text-gray-400 italic">
                          Wpisz treść wiadomości...
                        </span>
                      )}
                    </div>
                    <div className="flex justify-end text-xs text-gray-400 mt-4">
                      Teraz
                    </div>
                  </div>
                </div>
              </div>

              {/* Preview info */}
              <div className="mt-4 text-xs text-muted-foreground space-y-1">
                <p>
                  <strong>Encoding:</strong> {validation.encoding}
                </p>
                <p>
                  <strong>Długość:</strong> {validation.length} znaków
                </p>
                <p>
                  <strong>Segmenty:</strong> {validation.segments}
                </p>
                <p>
                  <strong>Koszt:</strong> {validation.segments}× stawka
                  pojedynczego SMS
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
