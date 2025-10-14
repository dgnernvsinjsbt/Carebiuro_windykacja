import Link from 'next/link';
import Sidebar from '@/components/Sidebar';
import { TemplateService } from '@/lib/templates/template-service';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Pencil, MessageCircle } from 'lucide-react';

export const dynamic = 'force-dynamic';

export default async function WhatsAppTemplatesPage() {
  const templates = await TemplateService.getTemplatesByChannel('whatsapp');

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

      {templates.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <MessageCircle className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg font-semibold mb-2">Brak szablonów WhatsApp</p>
            <p className="text-muted-foreground text-center">
              Nie znaleziono żadnych szablonów WhatsApp.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {templates.map((template) => (
            <Card key={template.id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <CardTitle className="text-lg">{template.name}</CardTitle>
                    <CardDescription className="text-xs">
                      Klucz: {template.template_key}
                    </CardDescription>
                  </div>
                  <Link href={`/szablony/whatsapp/${template.id}`}>
                    <Button variant="ghost" size="sm">
                      <Pencil className="h-4 w-4" />
                    </Button>
                  </Link>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {/* Body preview */}
                  {template.body_text && (
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-1">
                        Treść:
                      </p>
                      <p className="text-sm text-muted-foreground line-clamp-4 whitespace-pre-wrap">
                        {template.body_text}
                      </p>
                    </div>
                  )}

                  {/* Metadata */}
                  <div className="flex items-center justify-between pt-2 border-t">
                    <span className="text-xs text-muted-foreground">
                      {template.placeholders.length} zmiennych
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {new Date(template.updated_at).toLocaleDateString('pl-PL')}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
          </div>
        </div>
      </main>
    </div>
  );
}
