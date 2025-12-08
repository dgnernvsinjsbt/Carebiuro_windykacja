import { NextResponse } from 'next/server';
import { contactFormSchema } from '@/lib/validation';

export async function POST(request: Request) {
  try {
    const body = await request.json();

    // Validate request body
    const result = contactFormSchema.safeParse(body);

    if (!result.success) {
      return NextResponse.json(
        { error: 'Nieprawidłowe dane formularza', details: result.error.issues },
        { status: 400 }
      );
    }

    const { name, email, phone } = result.data;
    const timestamp = new Date().toISOString();

    // Send to Google Sheets webhook
    const webhookUrl = process.env.GOOGLE_SHEETS_WEBHOOK_URL;

    if (!webhookUrl || webhookUrl.includes('PLACEHOLDER')) {
      console.warn('Webhook URL not configured - skipping external request');
      // Return success anyway for development/demo purposes
      return NextResponse.json({
        success: true,
        message: 'Formularz zapisany (webhook nie skonfigurowany)',
      });
    }

    const webhookResponse = await fetch(webhookUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        name,
        email,
        phone,
        timestamp,
      }),
    });

    if (!webhookResponse.ok) {
      console.error('Webhook error:', await webhookResponse.text());
      throw new Error('Nie udało się wysłać danych do systemu');
    }

    return NextResponse.json({
      success: true,
      message: 'Formularz został wysłany pomyślnie',
    });
  } catch (error) {
    console.error('Contact form error:', error);
    return NextResponse.json(
      { error: 'Wystąpił błąd podczas przetwarzania formularza' },
      { status: 500 }
    );
  }
}
