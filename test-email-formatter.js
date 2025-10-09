// Quick test of email formatter
const { plainTextToHtml } = require('./lib/email-formatter.ts');

const testText = `Dzień dobry {{client_name}},

Informujemy, że na Państwa koncie wystawiliśmy fakturę {{invoice_number}} na kwotę {{amount}}. Termin: {{due_date}}.

Pozdrawiamy,
Carebiuro`;

console.log('=== INPUT ===');
console.log(testText);
console.log('\n=== OUTPUT HTML ===');
const html = plainTextToHtml(testText);
console.log(html);
console.log('\n=== HTML LENGTH ===');
console.log(html.length);
