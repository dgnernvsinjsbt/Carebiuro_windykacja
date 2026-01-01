import { NextRequest, NextResponse } from 'next/server';
import { fakturowniaApi } from '@/lib/fakturownia';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

/**
 * Parse Polish address string into components
 * Examples:
 * - "ul. Warszawska 15/3, 00-001 Warszawa, Polska"
 * - "Krakowska 42, 30-100 Kraków"
 * - "ul. Długa 5 m. 10, 01-234 Gdańsk, Poland"
 */
function parseAddress(address: string): {
  street: string;
  house_number: string;
  postal_code: string;
  city: string;
  country: string;
} {
  const result = {
    street: '',
    house_number: '',
    postal_code: '',
    city: '',
    country: 'Polska',
  };

  if (!address || address.trim() === '') {
    return result;
  }

  // Clean up the address
  let addr = address.trim();

  // Try to extract country (last part after comma)
  const parts = addr.split(',').map(p => p.trim());

  // Check if last part is a country
  const lastPart = parts[parts.length - 1]?.toLowerCase();
  const countryKeywords = ['polska', 'poland', 'niemcy', 'germany', 'deutschland'];
  if (parts.length > 1 && countryKeywords.some(c => lastPart.includes(c))) {
    result.country = parts.pop()!.trim();
  }

  // Try to find postal code and city (format: XX-XXX City or XXXXX City)
  const postalCityRegex = /(\d{2}-\d{3}|\d{5})\s+(.+)/;

  for (let i = parts.length - 1; i >= 0; i--) {
    const match = parts[i].match(postalCityRegex);
    if (match) {
      result.postal_code = match[1];
      result.city = match[2].trim();
      parts.splice(i, 1);
      break;
    }
  }

  // Remaining parts should be street and house number
  const streetPart = parts.join(', ').trim();

  if (streetPart) {
    // Remove "ul." prefix
    let cleanStreet = streetPart.replace(/^ul\.\s*/i, '');

    // Try to extract house number (last number/number with letter at the end)
    // Patterns: "15", "15A", "15/3", "15 m. 10", "15 m 10"
    const houseNumberRegex = /\s+(\d+[A-Za-z]?(?:\/\d+)?(?:\s*m\.?\s*\d+)?)$/;
    const houseMatch = cleanStreet.match(houseNumberRegex);

    if (houseMatch) {
      result.house_number = houseMatch[1].trim();
      result.street = cleanStreet.replace(houseNumberRegex, '').trim();
    } else {
      result.street = cleanStreet;
    }
  }

  return result;
}

/**
 * POST /api/sync/addresses
 * Fetch delivery addresses for clients by name
 *
 * Body: { names: string[], limit?: number }
 * Returns: { results: Array<{ name, found, client_id?, delivery_address?, parsed_address? }> }
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { names, limit = 10 } = body;

    if (!names || !Array.isArray(names) || names.length === 0) {
      return NextResponse.json(
        { success: false, error: 'names array is required' },
        { status: 400 }
      );
    }

    const namesToProcess = names.slice(0, limit);
    console.log(`[SyncAddresses] Processing ${namesToProcess.length} clients...`);

    const results: Array<{
      name: string;
      found: boolean;
      client_id?: number;
      delivery_address?: string;
      parsed_address?: {
        street: string;
        house_number: string;
        postal_code: string;
        city: string;
        country: string;
      };
      error?: string;
    }> = [];

    for (const name of namesToProcess) {
      try {
        console.log(`[SyncAddresses] Searching for: ${name}`);

        // Search client by name in Fakturownia
        const clients = await fakturowniaApi.searchClientsByName(name);

        if (clients.length === 0) {
          results.push({
            name,
            found: false,
            error: 'Client not found',
          });
          continue;
        }

        // Find exact match or best match
        let client = clients.find(c => c.name === name);
        if (!client) {
          // Try case-insensitive match
          client = clients.find(c => c.name.toLowerCase() === name.toLowerCase());
        }
        if (!client) {
          // Take first result
          client = clients[0];
        }

        console.log(`[SyncAddresses] Found client ${client.id}: ${client.name}`);

        // Use postal_address (adres korespondencyjny) - it's an object with structured fields
        const postalAddr = (client as any).postal_address;
        console.log(`[SyncAddresses] Postal address:`, postalAddr || '(empty)');

        // Extract street and house number from postal_address.street (e.g., "Bodzów 2/ 1")
        let street = '';
        let houseNumber = '';
        if (postalAddr?.street) {
          const streetParts = postalAddr.street.match(/^(.+?)\s+(\d+[A-Za-z]?(?:\s*\/\s*\d+)?)$/);
          if (streetParts) {
            street = streetParts[1].trim();
            houseNumber = streetParts[2].replace(/\s+/g, '').trim(); // Remove spaces: "2/ 1" -> "2/1"
          } else {
            street = postalAddr.street;
          }
        }

        results.push({
          name,
          found: true,
          client_id: client.id,
          delivery_address: postalAddr ? `${postalAddr.street}, ${postalAddr.post_code} ${postalAddr.city}` : '',
          parsed_address: {
            street: street,
            house_number: houseNumber,
            postal_code: postalAddr?.post_code || '',
            city: postalAddr?.city || '',
            country: postalAddr?.country || 'PL',
          },
        });

      } catch (err: any) {
        console.error(`[SyncAddresses] Error for ${name}:`, err.message);
        results.push({
          name,
          found: false,
          error: err.message,
        });
      }
    }

    const foundCount = results.filter(r => r.found).length;
    console.log(`[SyncAddresses] Completed: ${foundCount}/${namesToProcess.length} found`);

    return NextResponse.json({
      success: true,
      data: {
        total: namesToProcess.length,
        found: foundCount,
        not_found: namesToProcess.length - foundCount,
        results,
      },
    });

  } catch (error: any) {
    console.error('[SyncAddresses] Error:', error);
    return NextResponse.json(
      { success: false, error: error.message || 'Failed to sync addresses' },
      { status: 500 }
    );
  }
}
