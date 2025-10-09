import { NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase';

/**
 * DEBUG endpoint - shows exactly what's in the database
 * GET /api/debug/email-template?id=EMAIL_2
 */
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get('id') || 'EMAIL_2';

    const { data: template, error } = await supabaseAdmin()
      .from('email_templates')
      .select('*')
      .eq('id', id)
      .single();

    if (error || !template) {
      return NextResponse.json(
        { error: 'Template not found' },
        { status: 404 }
      );
    }

    return NextResponse.json({
      id: template.id,
      name: template.name,
      subject: template.subject,
      body_plain_length: template.body_plain?.length || 0,
      body_html_length: template.body_html?.length || 0,
      body_text_length: template.body_text?.length || 0,
      body_plain: template.body_plain,
      body_html: template.body_html,
      body_text: template.body_text,
      updated_at: template.updated_at,
    });
  } catch (error: any) {
    return NextResponse.json(
      { error: error.message },
      { status: 500 }
    );
  }
}
