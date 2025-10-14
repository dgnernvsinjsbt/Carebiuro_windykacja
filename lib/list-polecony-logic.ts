/**
 * List Polecony Logic
 *
 * Funkcje logiczne do identyfikacji klientów kwalifikujących się do listu poleconego
 *
 * Warunki eskalacji:
 * 1. Klient ma 3+ faktury z wysłanym trzecim (finalnym) upomnieniem (EMAIL_3, SMS_3 lub WHATSAPP_3)
 * 2. LUB Suma zadłużenia z faktur z trzecim upomnieniem >= 190 EUR
 */

import { Invoice, Client } from '@/types';
import { parseFiscalSync } from './fiscal-sync-parser';

/**
 * Sprawdza czy faktura ma wysłane trzecie upomnienie
 */
export function hasThirdReminder(invoice: Invoice): boolean {
  const fiscalSync = parseFiscalSync(invoice.internal_note);

  if (!fiscalSync) return false;

  // Sprawdź czy którykolwiek z trzecich poziomów został wysłany
  return fiscalSync.EMAIL_3 || fiscalSync.SMS_3 || fiscalSync.WHATSAPP_3;
}

/**
 * Sprawdza czy klient kwalifikuje się do listu poleconego
 *
 * @param client - Dane klienta
 * @param invoices - Lista faktur klienta
 * @param thresholdAmount - Próg kwotowy (domyślnie 190 EUR)
 * @returns true jeśli klient kwalifikuje się
 */
export function qualifiesForListPolecony(
  client: Client,
  invoices: Invoice[],
  thresholdAmount: number = 190
): boolean {
  // Filtruj faktury z trzecim upomnieniem
  const invoicesWithThirdReminder = invoices.filter(hasThirdReminder);

  // Warunek 1: 3+ faktury z trzecim upomnieniem
  if (invoicesWithThirdReminder.length >= 3) {
    return true;
  }

  // Warunek 2: Suma zadłużenia >= 190 EUR (z faktur z trzecim upomnieniem)
  // Obliczamy outstanding jako (total - paid) ponieważ outstanding jest GENERATED COLUMN w Supabase
  const totalDebt = invoicesWithThirdReminder.reduce((sum, invoice) => {
    const outstanding = (invoice.total || 0) - (invoice.paid || 0);
    return sum + outstanding;
  }, 0);

  if (totalDebt >= thresholdAmount) {
    return true;
  }

  return false;
}

/**
 * Pobiera listę faktur klienta z trzecim upomnieniem
 * (używane do generowania PDF-a)
 */
export function getInvoicesWithThirdReminder(invoices: Invoice[]): Invoice[] {
  return invoices.filter(hasThirdReminder);
}

/**
 * Oblicza całkowitą kwotę zadłużenia klienta (tylko faktury z trzecim upomnieniem)
 * Oblicza outstanding jako (total - paid) ponieważ outstanding jest GENERATED COLUMN w Supabase
 */
export function calculateTotalDebt(invoices: Invoice[]): number {
  const relevantInvoices = getInvoicesWithThirdReminder(invoices);

  return relevantInvoices.reduce((sum, invoice) => {
    const outstanding = (invoice.total || 0) - (invoice.paid || 0);
    return sum + outstanding;
  }, 0);
}

/**
 * Oblicza liczbę dni zwłoki dla faktury
 * Formuła: Dzień dzisiejszy - (Data wystawienia + 30 dni)
 */
export function calculateDelayDays(issueDate: string | null): number {
  if (!issueDate) return 0;

  const today = new Date();
  today.setHours(0, 0, 0, 0); // Zeruj godziny dla dokładności

  const issueDateObj = new Date(issueDate);
  issueDateObj.setHours(0, 0, 0, 0);

  // Dodaj 30 dni do daty wystawienia (termin płatności)
  const paymentDueDate = new Date(issueDateObj);
  paymentDueDate.setDate(paymentDueDate.getDate() + 30);

  // Oblicz różnicę w dniach
  const diffTime = today.getTime() - paymentDueDate.getTime();
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

  return diffDays > 0 ? diffDays : 0;
}

/**
 * Formatuje datę do formatu DD.MM.YYYY
 */
export function formatDate(dateString: string | null): string {
  if (!dateString) return '-';

  const date = new Date(dateString);
  const day = String(date.getDate()).padStart(2, '0');
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const year = date.getFullYear();

  return `${day}.${month}.${year}`;
}
