import { NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase';
import { revalidatePath } from 'next/cache';
import { z } from 'zod';
import { plainTextToHtml, plainTextToText } from '@/lib/email-formatter';

// Validation schema
const UpdateTemplateSchema = z.object({
  id: z.string(),
  subject: z.string().min(1, 'Temat nie może być pusty'),
  body_plain: z.string().min(1, 'Treść wiadomości nie może być pusta'),
});

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { id, subject, body_plain } = UpdateTemplateSchema.parse(body);

    console.log(`[UpdateTemplate] Updating template ${id}`);

    // Konwertuj plain text na HTML i text fallback
    const body_html = plainTextToHtml(body_plain);
    const body_text = plainTextToText(body_plain);

    console.log(`[UpdateTemplate] Converted plain text to HTML (${body_html.length} chars)`);

    // Update template in Supabase
    const { data, error } = await supabaseAdmin()
      .from('email_templates')
      .update({
        subject,
        body_plain,
        body_html,
        body_text,
        updated_at: new Date().toISOString(),
      })
      .eq('id', id)
      .select()
      .single();

    if (error) {
      console.error('[UpdateTemplate] Database error:', error);
      return NextResponse.json(
        { success: false, error: error.message },
        { status: 500 }
      );
    }

    console.log(`[UpdateTemplate] ✅ Template ${id} updated successfully`);

    // Revalidate pages
    revalidatePath('/settings/email-templates');
    revalidatePath(`/settings/email-templates/${id}`);

    return NextResponse.json({ success: true, data });
  } catch (error: any) {
    console.error('[UpdateTemplate] Error:', error);

    if (error instanceof z.ZodError) {
      return NextResponse.json(
        {
          success: false,
          error: 'Invalid request data',
          details: error.errors,
        },
        { status: 400 }
      );
    }

    return NextResponse.json(
      {
        success: false,
        error: error.message || 'Failed to update template',
      },
      { status: 500 }
    );
  }
}
