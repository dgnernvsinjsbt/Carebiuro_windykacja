import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { z } from 'zod';
import { plainTextToHtml, plainTextToText } from '@/lib/email-formatter';
import { revalidatePath } from 'next/cache';

const updateSchema = z.object({
  id: z.string().uuid(),
  channel: z.enum(['email', 'sms', 'whatsapp', 'letter']),
  subject: z.string().optional(),
  body_text: z.string().optional(),
  body_top: z.string().optional(),
  body_bottom: z.string().optional(),
});

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const validated = updateSchema.parse(body);

    const supabase = await createClient();

    // Prepare update object based on channel
    const updateData: Record<string, any> = {
      updated_at: new Date().toISOString(),
    };

    if (validated.channel === 'email') {
      // For email: update subject, body_text, and generate body_html
      if (validated.subject !== undefined) {
        updateData.subject = validated.subject;
      }
      if (validated.body_text !== undefined) {
        updateData.body_text = validated.body_text;
        updateData.body_html = plainTextToHtml(validated.body_text);
      }
    } else if (validated.channel === 'sms' || validated.channel === 'whatsapp') {
      // For SMS/WhatsApp: only body_text
      if (validated.body_text !== undefined) {
        updateData.body_text = validated.body_text;
      }
    } else if (validated.channel === 'letter') {
      // For letter: body_top and body_bottom
      if (validated.body_top !== undefined) {
        updateData.body_top = validated.body_top;
      }
      if (validated.body_bottom !== undefined) {
        updateData.body_bottom = validated.body_bottom;
      }
    }

    // Update in database
    const { error } = await supabase
      .from('message_templates')
      .update(updateData)
      .eq('id', validated.id);

    if (error) {
      console.error('Database error:', error);
      return NextResponse.json(
        { error: 'Failed to update template' },
        { status: 500 }
      );
    }

    // Revalidate paths
    // Map channel to URL path (letter -> list-polecony)
    const channelPath = validated.channel === 'letter' ? 'list-polecony' : validated.channel;
    revalidatePath(`/szablony/${channelPath}`);
    revalidatePath(`/szablony/${channelPath}/${validated.id}`);

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error updating template:', error);

    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', details: error.errors },
        { status: 400 }
      );
    }

    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
