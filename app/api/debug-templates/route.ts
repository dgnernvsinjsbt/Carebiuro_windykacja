import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const channel = searchParams.get('channel');

  const supabase = await createClient();

  const query = supabase
    .from('message_templates')
    .select('id, template_key, channel, name, is_active, created_at, body_text');

  if (channel) {
    query.eq('channel', channel);
  }

  const { data, error } = await query.order('channel').order('template_key');

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json(data || []);
}
