import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'

serve(async (req) => {
  try {
    // Skip auth check for testing
    const url = new URL(req.url)
    const count = parseInt(url.searchParams.get('count') || '1')
    const maxCount = 3 // Stop after 3 iterations

    console.log(`[Test] Iteration #${count}`)

    if (count >= maxCount) {
      console.log(`[Test] Reached max count (${maxCount}), stopping`)
      return new Response(
        JSON.stringify({
          success: true,
          message: `Finished at iteration ${count}`,
          count: count
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    }

    // Try to trigger next iteration
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!
    const serviceRoleKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    const nextUrl = `${supabaseUrl}/functions/v1/test-self-trigger?count=${count + 1}`

    console.log(`[Test] Triggering iteration #${count + 1}: ${nextUrl}`)

    // Fire and forget - don't await!
    fetch(nextUrl, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${serviceRoleKey}`,
        'Content-Type': 'application/json',
      },
    }).catch(err => console.error('[Test] Failed to trigger next iteration:', err))

    return new Response(
      JSON.stringify({
        success: true,
        message: `Iteration ${count} done, triggered ${count + 1}`,
        count: count,
        next_triggered: true
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    )
  } catch (error: any) {
    console.error('[Test] Error:', error)
    return new Response(
      JSON.stringify({ success: false, error: error.message }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    )
  }
})
