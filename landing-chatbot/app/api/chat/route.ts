import { NextRequest, NextResponse } from 'next/server';
import { findFAQMatch, getFAQContext, type FAQ } from '@/lib/faq-matcher';
import { streamChatCompletion, createTextStream, type Message } from '@/lib/openai';
import faqData from '@/public/faq.json';

const faqs: FAQ[] = faqData as FAQ[];

export const runtime = 'edge';

/**
 * Chat API endpoint
 * POST /api/chat
 * Body: { message: string, conversationHistory?: Message[] }
 * Returns: Streaming response (SSE format)
 */
export async function POST(req: NextRequest) {
  try {
    // Parse request body
    const body = await req.json();
    const { message, conversationHistory = [] } = body;

    if (!message || typeof message !== 'string') {
      return NextResponse.json(
        { error: 'Message is required and must be a string' },
        { status: 400 }
      );
    }

    // Step 1: Try to find exact FAQ match
    const faqMatch = findFAQMatch(message, faqs);

    if (faqMatch) {
      // FAQ match found - return instant answer
      console.log(`[Chat API] FAQ match found: ${faqMatch.question}`);

      // Create streaming response from FAQ answer
      const stream = createTextStream(faqMatch.answer);

      return new NextResponse(stream, {
        headers: {
          'Content-Type': 'text/plain; charset=utf-8',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
        },
      });
    }

    // Step 2: No FAQ match - use OpenAI with FAQ context
    console.log('[Chat API] No FAQ match, using OpenAI');

    // Check if OpenAI API key is configured
    if (!process.env.OPENAI_API_KEY) {
      // Return friendly fallback message instead of error
      const fallbackMessage = 'Dziękujemy za pytanie! Aby uzyskać szczegółowe informacje, skontaktuj się z nami bezpośrednio: kontakt@twojebezpieczenstwo.pl lub zadzwoń.';
      const stream = createTextStream(fallbackMessage);

      return new NextResponse(stream, {
        headers: {
          'Content-Type': 'text/plain; charset=utf-8',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
        },
      });
    }

    // Prepare messages for OpenAI
    const messages: Message[] = [
      ...conversationHistory.slice(-6), // Keep last 6 messages for context
      { role: 'user', content: message },
    ];

    // Get FAQ context for system prompt
    const faqContext = getFAQContext(faqs);

    // Stream response from OpenAI
    const stream = await streamChatCompletion(messages, faqContext);

    return new NextResponse(stream, {
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
      },
    });
  } catch (error) {
    console.error('[Chat API] Error:', error);

    // Return friendly error message as stream instead of JSON error
    const errorMessage = 'Przepraszamy, wystąpił problem z połączeniem. Spróbuj ponownie lub skontaktuj się bezpośrednio: kontakt@twojebezpieczenstwo.pl';
    const stream = createTextStream(errorMessage);

    return new NextResponse(stream, {
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
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
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}
