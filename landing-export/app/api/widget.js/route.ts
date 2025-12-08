import { NextRequest, NextResponse } from 'next/server';
import { readFile } from 'fs/promises';
import { join } from 'path';

export const dynamic = 'force-static';

/**
 * Serve the chatbot widget JavaScript file
 * GET /api/widget.js
 * Returns: JavaScript file with CORS headers
 */
export async function GET(req: NextRequest) {
  try {
    // Read the widget.js file from public directory
    const widgetPath = join(process.cwd(), 'public', 'widget.js');
    const widgetContent = await readFile(widgetPath, 'utf-8');

    // Return as JavaScript with CORS headers
    return new NextResponse(widgetContent, {
      headers: {
        'Content-Type': 'application/javascript; charset=utf-8',
        'Cache-Control': 'public, max-age=3600', // Cache for 1 hour
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
      },
    });
  } catch (error) {
    console.error('[Widget API] Error serving widget:', error);

    return new NextResponse('// Widget failed to load', {
      status: 500,
      headers: {
        'Content-Type': 'application/javascript',
      },
    });
  }
}

/**
 * Handle OPTIONS requests for CORS
 */
export async function OPTIONS() {
  return new NextResponse(null, {
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}
