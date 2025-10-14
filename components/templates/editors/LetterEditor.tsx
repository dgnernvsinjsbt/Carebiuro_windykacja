'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import type { MessageTemplate } from '@/lib/templates/types';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Save, X, Info } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface LetterEditorProps {
  template: MessageTemplate;
}

export function LetterEditor({ template }: LetterEditorProps) {
  const router = useRouter();
  const [bodyTop, setBodyTop] = useState(template.body_top || '');
  const [bodyBottom, setBodyBottom] = useState(template.body_bottom || '');
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
          channel: 'letter',
          body_top: bodyTop,
          body_bottom: bodyBottom,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to save template');
      }

      router.push('/szablony/list-polecony');
      router.refresh();
    } catch (err: any) {
      setError(err.message);
      setSaving(false);
    }
  }

  return (
    <div className="max-w-5xl space-y-6">
      {/* Info alert */}
      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          Edytuj tylko tekst NAD i POD tabelą faktur. Układ dokumentu, nagłówek i tabela
          są generowane automatycznie.
        </AlertDescription>
      </Alert>

      {/* Error message */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-5">
        {/* Editor - 3 cols */}
        <div className="lg:col-span-3 space-y-6">
          <Card>
            <CardContent className="pt-6 space-y-6">
              {/* Body top */}
              <div className="space-y-2">
                <Label htmlFor="top">
                  Tekst wprowadzający (nad tabelą faktur)
                </Label>
                <Textarea
                  id="top"
                  value={bodyTop}
                  onChange={(e) => setBodyTop(e.target.value)}
                  rows={4}
                  placeholder="Szanowni Państwo, działając w imieniu naszego Klienta, wzywamy do zapłaty następujących należności..."
                />
              </div>

              {/* Body bottom */}
              <div className="space-y-2">
                <Label htmlFor="bottom">
                  Tekst końcowy (pod tabelą faktur)
                </Label>
                <Textarea
                  id="bottom"
                  value={bodyBottom}
                  onChange={(e) => setBodyBottom(e.target.value)}
                  rows={8}
                  placeholder={`Termin zapłaty: 7 dni od otrzymania niniejszego wezwania.

W przypadku nieuregulowania należności w wyznaczonym terminie, sprawa zostanie skierowana na drogę postępowania sądowego...`}
                />
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

        {/* Preview - 2 cols */}
        <div className="lg:col-span-2">
          <Card>
            <CardContent className="pt-6">
              <h3 className="font-medium mb-4">Podgląd dokumentu</h3>

              {/* Document preview */}
              <div className="bg-white border rounded-md p-6 text-sm space-y-4 max-h-[600px] overflow-y-auto">
                {/* Header (static) */}
                <div className="text-center border-b pb-4">
                  <p className="font-bold text-lg">PRZEDSĄDOWE WEZWANIE DO ZAPŁATY</p>
                </div>

                {/* Top text */}
                <div className="whitespace-pre-wrap">
                  {bodyTop || (
                    <p className="text-muted-foreground italic">
                      Tekst wprowadzający...
                    </p>
                  )}
                </div>

                {/* Table (static example) */}
                <Table className="text-xs">
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-xs">Nr faktury</TableHead>
                      <TableHead className="text-xs">Wystawiono</TableHead>
                      <TableHead className="text-xs">Termin</TableHead>
                      <TableHead className="text-right text-xs">Kwota</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow>
                      <TableCell>FV/2024/10/001</TableCell>
                      <TableCell>01.10.24</TableCell>
                      <TableCell>15.10.24</TableCell>
                      <TableCell className="text-right">2,500 PLN</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell colSpan={3} className="text-right font-bold">
                        Suma:
                      </TableCell>
                      <TableCell className="text-right font-bold">
                        2,500 PLN
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>

                {/* Bottom text */}
                <div className="whitespace-pre-wrap">
                  {bodyBottom || (
                    <p className="text-muted-foreground italic">Tekst końcowy...</p>
                  )}
                </div>

                {/* Footer (static) */}
                <div className="border-t pt-4 text-xs">
                  <p>Z poważaniem,</p>
                  <p className="font-medium mt-1">CBB-OFFICE GmbH</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
