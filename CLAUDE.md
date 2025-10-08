CLAUDE.md — Best Practices for Fiscal Development
🎯 Core Principles
1. Plan First, Code Second

Zanim napiszesz choć jedną linijkę kodu, przeczytaj cały opis funkcji.

Podziel pracę na najmniejsze logiczne kroki.

Zapisz pseudokod lub szkic przepływu danych.

Zidentyfikuj zależności między modułami (np. Supabase ↔ Fakturownia ↔ n8n).

2. Small Steps, Frequent Checks

Implementuj jedną funkcję na raz.

Testuj natychmiast po każdej zmianie.

Nie przechodź dalej, dopóki obecny etap nie działa.

Jeśli coś się psuje → zatrzymaj się, przeczytaj błąd, zrozum przyczynę.

3. Think Like a Product Engineer

Zawsze pytaj „po co”, zanim coś dodasz.

Myśl o przypadkach brzegowych (np. pusta faktura, brak klienta, limit API).

Dbaj o doświadczenie użytkownika — system ma być prosty i zrozumiały.

Kod powinien tłumaczyć się sam przez nazwy funkcji i zmiennych.

4. Communication is Key

Jeśli coś jest niejasne → pytaj, nie zakładaj.

Wyjaśnij swój plan przed implementacją.

Dziel się postępami po każdym większym kroku.

Dokumentuj decyzje i kompromisy (np. „parsowanie komentarzy zamiast webhooków”).

🔄 Development Workflow
Stage 1: Planning

Przeczytaj wymagania funkcji.

Zrób listę plików do utworzenia lub modyfikacji.

Zanotuj potencjalne problemy (np. limity API Fakturowni).

Zadaj pytania, zanim zaczniesz pisać.

Potwierdź plan.

Stage 2: Implementation

Stwórz strukturę folderów i plików.

Zaimplementuj najmniejszy element (np. pojedynczy node w n8n).

Przetestuj w izolacji.

Dopiero wtedy zintegruj z resztą systemu.

Testuj ponownie.

Utwórz checkpoint commit.

Stage 3: Validation

Uruchom aplikację lokalnie lub w stagingu.

Sprawdź konsolę (brak błędów i ostrzeżeń).

Przetestuj ścieżkę „happy path” + edge cases.

Popraw błędy natychmiast.

Zapisz co działa.

Stage 4: Checkpoint

Podsumuj, co zostało wdrożone.

Wypisz, co działa, a co nie.

Zapisz dług techniczny (np. „refactor parsera komentarzy”).

Potwierdź gotowość do następnego modułu.

🛠️ Technical Best Practices
File Organization

✅ DO

Jeden komponent / plik.

Grupy po funkcjonalności (np. /fakturownia-sync, /client-ui, /supabase-hooks).

Nazwy opisowe: UpdateCommentNode.ts, InvoiceParser.ts.

❌ DON’T

Jeden plik z dziesiątkami funkcji.

Nazwy generyczne jak utils.ts z 500 liniami.

Głębokie zagnieżdżenia (max 3–4 poziomy).

Code Style (TypeScript / Python / JS)

✅ DO

async function syncInvoiceComment(invoiceId: string, field: string, value: boolean) {
  const invoice = await getInvoice(invoiceId);
  const updatedComment = updateFiscalSync(invoice.comment, field, value);
  await fakturownia.put(`/invoices/${invoiceId}`, { invoice: { comment: updatedComment } });
}


❌ DON’T

async function doSync(id, f, v) {
  const x = await api(id);
  await send(x, f, v);
}

Error Handling

✅ DO

try {
  const res = await supabase.from('invoices').select('*');
  if (!res.data) throw new Error('No data returned');
} catch (err) {
  console.error('Fetch error:', err);
  toast.error('Nie udało się pobrać danych z bazy');
}


❌ DON’T

const res = await supabase.from('invoices').select('*'); // bez obsługi błędu

Component Structure

✅ DO

export default async function DashboardPage() {
  const clients = await getClientsFromSupabase();
  return <ClientList clients={clients} />;
}


❌ DON’T

'use client';
export default function DashboardPage() {
  const [clients, setClients] = useState([]);
  useEffect(() => { fetch('/api/clients').then(r => r.json()).then(setClients); }, []);
});

🐛 Debugging Process

Zatrzymaj się. Nie pisz kolejnych linijek.

Odczytaj błąd dosłownie.

Cofnij się do ostatniej zmiany.

Odizoluj problem — wykomentuj kod.

Napraw przyczynę, nie objaw.

Zrozum dlaczego się zepsuło.

📋 Checkpoint System

Po każdej większej funkcji dodaj notatkę:

## Checkpoint: Fakturownia Sync — 2025-10-05

### ✅ Completed
- Dodano parser komentarzy `[FISCAL_SYNC]`
- Obsługa STOP flagi
- Aktualizacja Supabase po kliknięciu w UI

### 🐛 Known Issues
- Czasem zbyt częste wywołania API przy wielu kliknięciach

### 📝 Next Steps
- Debounce wywołania
- Dodać logi wysyłki w Supabase

🎨 UI/UX Standards

Każda akcja użytkownika → feedback (toast.success / toast.error).

Komponenty mają stany: loading, error, empty.

Interfejs responsywny (mobile / desktop).

Brak skoków layoutu przy wczytywaniu danych.

🔒 Security & Data

Waliduj dane wejściowe (Zod, Supabase policies).

Autoryzacja po stronie serwera (Next.js API Routes).

Nie loguj tokenów API.

Wrażliwe dane (np. NIP, e-mail) — tylko na poziomie autoryzowanego użytkownika.

Przy integracjach (np. Fakturownia API) respektuj limity 1000 req/h.

🚀 Performance

Pobieraj tylko potrzebne kolumny (select('id,status,total')).

Limituj zapytania (paginacja / per_page).

Buforuj dane w Supabase lub w RAMie aplikacji.

Używaj memoizacji (useMemo, useSWR).

Optymalizuj obrazy (next/image).

🧪 Testing Checklist

Happy Path

 Wysłanie e-maila / SMS działa poprawnie.

 Komentarz aktualizuje się w Fakturowni.

 Dane są zgodne w Supabase.

Edge Cases

 Brak klienta / faktury.

 Faktura z pustym komentarzem.

 Limit API osiągnięty.

Error Handling

 Błędy są widoczne w UI.

 System nie wiesza się przy awarii Fakturowni.

📚 Context Management

Przed każdą funkcją zapytaj:

Dlaczego to robimy?

Kto będzie tego używać? (księgowa, pracownik, system automatyczny)

Jak często to będzie wykonywane?

Jak rozpoznać sukces?

Jakie ograniczenia (API, czas, dane)?

🎓 Learning from Mistakes

Każdy większy błąd → dokumentuj.

## Lesson Learned: Zduplikowane wysyłki e-maili
**Data**: 2025-10-05  
**Przyczyna**: Brak blokady przy wielokrotnym kliknięciu przycisku.  
**Naprawa**: Dodano debounce + `isSending` state.  
**Wniosek**: Każda akcja API musi mieć blokadę ponownego kliknięcia.

🏁 Definition of Done

Feature jest gotowy, gdy:

 Działa poprawnie (happy + edge cases).

 Brak błędów w konsoli.

 UI spójny z resztą aplikacji.

 Kod czysty, bez TODO.

 Typy uzupełnione, brak any.

 Testy ręczne zakończone sukcesem.

 Checkpoint utworzony.

🎯 Daily Workflow Template
## Start
- [ ] Przeczytaj ostatni checkpoint
- [ ] Ustal max 3 cele na dziś
- [ ] Sprawdź ewentualne blokery

## W trakcie
- [ ] Koduj małymi krokami
- [ ] Testuj każdy etap
- [ ] Twórz checkpointy

## Koniec dnia
- [ ] Sprawdź integrację modułów
- [ ] Zaktualizuj główny checkpoint
- [ ] Zapisz pytania / blokery

💡 Pro Tips

Produktowo

Jeden cel → jedna sesja pracy.

Zrób najprostsze działające rozwiązanie, potem ulepszaj.

Kodowo

Czytaj swój kod na głos — znajdziesz błędy.

Upraszczaj — złożoność to koszt.

Nie bój się kasować — kod to nie relikwia.

Komunikacja

Lepiej zapytać 2× niż zgadywać raz.

Pokazuj — zrzuty ekranu > opisy.

🚨 Red Flags

Zatrzymaj się i zapytaj, jeśli:

utknąłeś na > 30 min,

masz pomysł „obejścia” trzeciego błędu,

nie wiesz, jak coś powinno działać,

masz zamiar „tymczasowo” dodać hardkodowane dane.

🎬 Pre-Launch Checklist

Funkcjonalność

 Sync z Fakturownią działa w obie strony

 Supabase poprawnie zapisuje dane

 Komentarze [FISCAL_SYNC] generują się prawidłowo

UX

 Wszystkie akcje mają feedback

 Stany loading/error/empty zaimplementowane

 Interfejs prosty dla nietechnicznych użytkowników

Performance

 API < 1000 req/h

 Czas ładowania < 2 s

 Brak nadmiarowych zapytań

Security

 Dane klientów chronione

 Klucze API w .env

 RLS w Supabase działa

Dokumentacja

 README + .env.example aktualne

 Endpointy API opisane

 Znane problemy zarejestrowane

📖 Remember

Make it work → Make it right → Make it fast.

Najpierw zrób, żeby działało.
Potem zadbaj o jakość i bezpieczeństwo.
Na końcu optymalizuj.

Perfect is the enemy of shipped.

Nie potrzebujesz perfekcji, tylko działającego systemu,
który realnie pomaga biurom księgowym.

✅ Sukces =

Funkcja działa i jest stabilna.

Kod jest zrozumiały tydzień później.

Klient widzi efekt („wow, działa automatycznie”).

Ty rozumiesz każdy element, który napisałeś.

Now go build Fiscal the smart way. 🧠⚡
Plan → Test → Document → Ship.