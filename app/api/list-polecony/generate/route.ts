/**
 * API Endpoint: Generate List Polecony Documents (PDF + Excel + ZIP)
 *
 * POST /api/list-polecony/generate
 * Body: { clientIds: number[] }
 *
 * Generuje:
 * - Osobne PDF-y dla każdego klienta (1.pdf, 2.pdf, ...)
 * - Plik Excel z danymi klientów (od wiersza 3)
 * - Archiwum ZIP z wszystkimi plikami
 */

import { NextRequest, NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase';
import { generateListPoleconyHTML } from '@/lib/pdf-generator';
import { getInvoicesWithThirdReminder, calculateTotalDebt } from '@/lib/list-polecony-logic';
import puppeteer from 'puppeteer';
import ExcelJS from 'exceljs';
import archiver from 'archiver';
import { Readable } from 'stream';
import fs from 'fs';
import path from 'path';
import os from 'os';

// Force dynamic rendering - don't evaluate at build time
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function POST(request: NextRequest) {
  try {
    let clientIds: number[] = [];

    // Sprawdź czy request ma body
    const contentType = request.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      const body = await request.json();
      clientIds = body.clientIds;
    }

    console.log('[ListPolecony API] Otrzymano request z clientIds:', clientIds);

    if (!clientIds || !Array.isArray(clientIds) || clientIds.length === 0) {
      return NextResponse.json(
        { success: false, error: 'Brak wybranych klientów' },
        { status: 400 }
      );
    }

    console.log(`Generowanie dokumentów dla ${clientIds.length} klientów...`);

    // Pobierz dane klientów i faktur z Supabase
    const { data: clients, error: clientsError } = await supabaseAdmin
      .from('clients')
      .select('*')
      .in('id', clientIds)
      .order('name', { ascending: true }); // Sortowanie alfabetyczne

    if (clientsError || !clients) {
      console.error('Błąd pobierania klientów:', clientsError);
      return NextResponse.json(
        { success: false, error: 'Błąd pobierania danych klientów' },
        { status: 500 }
      );
    }

    const { data: invoices, error: invoicesError } = await supabaseAdmin
      .from('invoices')
      .select('*')
      .in('client_id', clientIds);

    if (invoicesError || !invoices) {
      console.error('Błąd pobierania faktur:', invoicesError);
      return NextResponse.json(
        { success: false, error: 'Błąd pobierania faktur' },
        { status: 500 }
      );
    }

    // Stwórz katalog tymczasowy dla plików
    const tempDir = path.join(os.tmpdir(), `list-polecony-${Date.now()}`);
    fs.mkdirSync(tempDir, { recursive: true });

    console.log(`Katalog tymczasowy: ${tempDir}`);

    // Uruchom Puppeteer
    const browser = await puppeteer.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox'],
    });

    try {
      // Generuj PDF-y dla każdego klienta
      const pdfPromises = clients.map(async (client, index) => {
        const clientInvoices = invoices.filter((inv) => inv.client_id === client.id);

        // Generuj HTML
        const html = generateListPoleconyHTML({
          client,
          invoices: clientInvoices,
        });

        // Generuj PDF za pomocą Puppeteer
        const page = await browser.newPage();
        await page.setContent(html, { waitUntil: 'networkidle0' });

        const pdfBuffer = await page.pdf({
          format: 'A4',
          printBackground: true,
          margin: {
            top: '1.5cm',
            right: '1.5cm',
            bottom: '1.5cm',
            left: '1.5cm',
          },
        });

        await page.close();

        // Zapisz PDF do pliku
        const pdfFilename = `${index + 1}.pdf`;
        const pdfPath = path.join(tempDir, pdfFilename);
        fs.writeFileSync(pdfPath, pdfBuffer);

        console.log(`Wygenerowano PDF: ${pdfFilename} dla klienta ${client.name}`);

        return {
          client,
          pdfFilename,
          invoiceCount: getInvoicesWithThirdReminder(clientInvoices).length,
          totalDebt: calculateTotalDebt(clientInvoices),
        };
      });

      const pdfResults = await Promise.all(pdfPromises);

      // Wczytaj szablon Excel zamiast tworzyć od zera
      const workbook = new ExcelJS.Workbook();
      const templatePath = path.join(process.cwd(), 'szablon_neolist.xlsx');
      await workbook.xlsx.readFile(templatePath);
      const worksheet = workbook.worksheets[0];

      // Usuń istniejące wiersze z danymi (wiersz 3 i dalej), zachowaj tylko nagłówki
      const rowsToDelete: number[] = [];
      worksheet.eachRow((row, rowNumber) => {
        if (rowNumber > 2) {
          rowsToDelete.push(rowNumber);
        }
      });
      // Usuwaj od końca, żeby nie zepsuć numeracji
      for (let i = rowsToDelete.length - 1; i >= 0; i--) {
        worksheet.spliceRows(rowsToDelete[i], 1);
      }

      // Wiersze 3+: Dane klientów
      pdfResults.forEach((result, index) => {
        const { client } = result;
        const invoice = invoices.find((inv) => inv.client_id === client.id);

        // Parsuj dane adresowe - wyciągnij numer budynku i lokalu z ulicy
        const street = invoice?.buyer_street || '';
        const streetParts = street.match(/^(.+?)\s+(\d+)(?:\/(\d+))?$/);
        const streetName = streetParts ? streetParts[1] : street;
        const houseNumber = streetParts ? streetParts[2] : '';
        const flatNumber = streetParts ? (streetParts[3] || '') : '';

        // Numer wiersza = 3 + index (wiersz 1 = nagłówki sekcji, wiersz 2 = nazwy kolumn)
        const rowNumber = 3 + index;
        const row = worksheet.getRow(rowNumber);

        // Wypełnij komórki dokładnie jak w szablonie
        row.getCell(1).value = 'Sz.P.';                                  // A - Zwrot grzecznościowy
        row.getCell(2).value = 100000245;                                // B - Envelo ID (zawsze takie samo)
        row.getCell(3).value = client.first_name || invoice?.buyer_name?.split(' ')[0] || ''; // C - Imię (z klienta lub faktury)
        row.getCell(4).value = client.last_name || invoice?.buyer_name?.split(' ').slice(1).join(' ') || ''; // D - Nazwisko (z klienta lub faktury)
        row.getCell(5).value = client.name;                              // E - Nazwa firmy
        row.getCell(6).value = streetName || null;                       // F - Ulica lub skrytka pocztowa
        row.getCell(7).value = houseNumber || null;                      // G - Nr budynku
        row.getCell(8).value = flatNumber || null;                       // H - Nr lokalu
        row.getCell(9).value = invoice?.buyer_post_code || null;         // I - Kod pocztowy
        row.getCell(10).value = invoice?.buyer_city || null;             // J - Miasto
        row.getCell(11).value = invoice?.buyer_country || 'Polska';      // K - Kraj
        row.getCell(12).value = 1;                                       // L - Typ produktu
        row.getCell(13).value = 'Y';                                     // M - Przesyłka rejestrowana
        row.getCell(14).value = null;                                    // N - Wycofane (puste)
        row.getCell(15).value = 'Y';                                     // O - ZPO
        row.getCell(16).value = 1;                                       // P - ID szablonu papeterii listu
        row.getCell(17).value = null;                                    // Q - ID szablonu treści (puste)
        row.getCell(18).value = `${index + 1}.pdf`;                      // R - Wskazanie nazwy pliku PDF
        row.getCell(19).value = 'Y';                                     // S - Kolor
        row.getCell(20).value = 'S';                                     // T - Duplex
        row.getCell(21).value = 'Y';                                     // U - Nadruk adresu na osobnej kartce
        row.getCell(22).value = 'Y';                                     // V - Generowanie strony adresowej
        row.getCell(23).value = 'Test';                                  // W - Tekst ZPO
        row.getCell(24).value = 'Ins_A';                                 // X - Identyfikator insertu
        row.getCell(25).value = 'Papier_1';                              // Y - Identyfikator papieru
        row.getCell(26).value = null;                                    // Z - Pole informacyjne nadawcy (puste)

        row.commit();
      });

      // Zapisz Excel do pliku
      const excelPath = path.join(tempDir, 'lista_klientow.xlsx');
      await workbook.xlsx.writeFile(excelPath);

      console.log('Wygenerowano plik Excel');

      // Stwórz archiwum ZIP
      const zipPath = path.join(tempDir, 'list-polecony.zip');
      const output = fs.createWriteStream(zipPath);
      const archive = archiver('zip', { zlib: { level: 9 } });

      archive.pipe(output);

      // Dodaj wszystkie PDF-y
      pdfResults.forEach((result) => {
        const pdfPath = path.join(tempDir, result.pdfFilename);
        archive.file(pdfPath, { name: result.pdfFilename });
      });

      // Dodaj Excel
      archive.file(excelPath, { name: 'lista_klientow.xlsx' });

      await archive.finalize();

      // Czekaj aż ZIP zostanie zapisany
      await new Promise<void>((resolve, reject) => {
        output.on('close', () => resolve());
        output.on('error', reject);
      });

      console.log('Utworzono archiwum ZIP');

      // Odczytaj ZIP jako buffer
      const zipBuffer = fs.readFileSync(zipPath);

      // Usuń pliki tymczasowe
      await browser.close();
      fs.rmSync(tempDir, { recursive: true, force: true });

      console.log('Usunięto pliki tymczasowe');

      // Aktualizuj flagę [LIST_POLECONY]true dla wygenerowanych klientów
      console.log('Aktualizowanie flag [LIST_POLECONY] dla klientów...');
      const { setListPolecony } = await import('@/lib/client-flags');
      const { fakturowniaApi } = await import('@/lib/fakturownia');

      const updatePromises = clients.map(async (client) => {
        try {
          // Zaktualizuj note z flagą (wszystkie 3 flagi w jednej linii)
          const updatedNote = setListPolecony(client.note, true);
          console.log(`[Update] Client ${client.id} - old note:`, client.note);
          console.log(`[Update] Client ${client.id} - new note:`, updatedNote);

          // 1. Zaktualizuj w Supabase
          const { data, error } = await supabaseAdmin
            .from('clients')
            .update({ note: updatedNote })
            .eq('id', client.id)
            .select();

          if (error) {
            console.error(`✗ Supabase update error for client ${client.id}:`, error);
          } else {
            console.log(`✓ Zaktualizowano flagę LIST_POLECONY w Supabase dla klienta ${client.id}`, data);
          }

          // 2. Zaktualizuj w Fakturowni
          await fakturowniaApi.updateClient(client.id, {
            note: updatedNote
          });

          console.log(`✓ Zaktualizowano flagę LIST_POLECONY w Fakturowni dla klienta ${client.id}`);
        } catch (err) {
          console.error(`✗ Błąd aktualizacji klienta ${client.id}:`, err);
        }
      });

      await Promise.all(updatePromises);
      console.log('Zakończono aktualizację flag klientów');

      // Aktualizuj flagę [LIST_POLECONY_SENT] na fakturach z trzecim upomnieniem
      console.log('Aktualizowanie flag [LIST_POLECONY_SENT] na fakturach...');
      const { setListPoleconyDate } = await import('@/lib/list-polecony-sent-parser');
      const today = new Date();

      const invoiceUpdatePromises = pdfResults.map(async (result) => {
        // Pobierz faktury klienta z bazy
        const clientInvoices = invoices.filter((inv) => inv.client_id === result.client.id);
        const invoicesWithThirdReminder = clientInvoices.filter(inv =>
          inv.has_third_reminder === true
        );

        for (const invoice of invoicesWithThirdReminder) {
          try {
            // Dodaj flagę [LIST_POLECONY_SENT]data do komentarza
            const updatedComment = setListPoleconyDate(invoice.comment || '', today);

            console.log(`[Update Invoice] ${invoice.id} - old comment:`, invoice.comment);
            console.log(`[Update Invoice] ${invoice.id} - new comment:`, updatedComment);

            // 1. Zaktualizuj w Supabase
            const { error: supError } = await supabaseAdmin
              .from('invoices')
              .update({
                comment: updatedComment,
                list_polecony_sent_date: today.toISOString()
              })
              .eq('id', invoice.id);

            if (supError) {
              console.error(`✗ Supabase update error for invoice ${invoice.id}:`, supError);
            } else {
              console.log(`✓ Zaktualizowano flagę LIST_POLECONY_SENT w Supabase dla faktury ${invoice.id}`);
            }

            // 2. Zaktualizuj w Fakturowni
            await fakturowniaApi.updateInvoice(invoice.id, {
              internal_note: updatedComment
            });

            console.log(`✓ Zaktualizowano flagę LIST_POLECONY_SENT w Fakturowni dla faktury ${invoice.id}`);
          } catch (err) {
            console.error(`✗ Błąd aktualizacji faktury ${invoice.id}:`, err);
          }
        }
      });

      await Promise.all(invoiceUpdatePromises);
      console.log('Zakończono aktualizację flag na fakturach');

      // Zwróć ZIP jako response
      return new NextResponse(zipBuffer, {
        headers: {
          'Content-Type': 'application/zip',
          'Content-Disposition': 'attachment; filename="list-polecony.zip"',
        },
      });
    } catch (error) {
      await browser.close();
      fs.rmSync(tempDir, { recursive: true, force: true });
      throw error;
    }
  } catch (error: any) {
    console.error('Błąd generowania dokumentów:', error);
    return NextResponse.json(
      {
        success: false,
        error: 'Błąd generowania dokumentów',
        details: error.message,
      },
      { status: 500 }
    );
  }
}
