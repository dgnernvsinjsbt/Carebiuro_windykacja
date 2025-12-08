import OpenAI from 'openai';

// Initialize OpenAI client
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY || '',
});

export interface Message {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

/**
 * Stream chat completion from OpenAI with FAQ context
 */
export async function streamChatCompletion(
  messages: Message[],
  faqContext: string
): Promise<ReadableStream<Uint8Array>> {
  // Prepare system message with FAQ context
  const systemMessage: Message = {
    role: 'system',
    content: `Jesteś asystentem dla polskich opiekunek pracujących w Niemczech.
Pomagasz z pytaniami o Gewerbe, legalną pracę, ubezpieczenia i wszystkie aspekty zatrudnienia.

Odpowiadaj:
- Po polsku
- Zwięźle (2-4 zdania)
- Pomocnie i przyjaźnie
- Opieraj się na dostarczonej bazie wiedzy FAQ
- Jeśli nie masz pewności, zasugeruj kontakt bezpośredni

Baza wiedzy FAQ:

${faqContext}

Jeśli użytkownik pyta o coś poza zakresem FAQ, odpowiedz ogólnie i zachęć do kontaktu.`,
  };

  // Create OpenAI stream
  const stream = await openai.chat.completions.create({
    model: 'gpt-4o',
    messages: [systemMessage, ...messages],
    temperature: 0.7,
    max_tokens: 500,
    stream: true,
  });

  // Convert OpenAI stream to Web ReadableStream
  const encoder = new TextEncoder();

  return new ReadableStream({
    async start(controller) {
      try {
        for await (const chunk of stream) {
          const content = chunk.choices[0]?.delta?.content || '';
          if (content) {
            controller.enqueue(encoder.encode(content));
          }
        }
        controller.close();
      } catch (error) {
        controller.error(error);
      }
    },
  });
}

/**
 * Generate a simple non-streaming response (for FAQ matches)
 */
export function createTextStream(text: string): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();

  return new ReadableStream({
    start(controller) {
      // Simulate streaming by sending text in chunks
      const words = text.split(' ');
      let currentChunk = '';

      for (let i = 0; i < words.length; i++) {
        currentChunk += words[i] + ' ';

        // Send chunks of ~5 words for smooth streaming effect
        if ((i + 1) % 5 === 0 || i === words.length - 1) {
          controller.enqueue(encoder.encode(currentChunk));
          currentChunk = '';
        }
      }

      controller.close();
    },
  });
}

export default openai;
