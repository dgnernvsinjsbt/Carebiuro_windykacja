import { supabaseAdmin } from '@/lib/supabase';
import Sidebar from '@/components/Sidebar';
import EmailTemplateEditor from '@/components/EmailTemplateEditor';
import { notFound } from 'next/navigation';

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function EditTemplatePage({ params }: PageProps) {
  const { id } = await params;

  const { data: template, error } = await supabaseAdmin()
    .from('email_templates')
    .select('*')
    .eq('id', id)
    .single();

  if (error || !template) {
    notFound();
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <main className="flex-1 p-8">
        <EmailTemplateEditor template={template} />
      </main>
    </div>
  );
}
