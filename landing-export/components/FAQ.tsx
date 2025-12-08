'use client';

import { useState } from 'react';

interface FAQItem {
  question: string;
  answer: string;
}

const faqData: FAQItem[] = [
  {
    question: 'Czy moje zatrudnienie jest w pełni legalne?',
    answer:
      'Tak, zapewniamy pełną legalność zatrudnienia. Wszystkie dokumenty są przygotowywane zgodnie z niemieckim prawem pracy. Pomagamy w założeniu Gewerbe oraz rejestracjach we wszystkich wymaganych instytucjach.',
  },
  {
    question: 'Jakie ubezpieczenie jest zapewnione?',
    answer:
      'Oferujemy kompleksowe ubezpieczenie obejmujące: ubezpieczenie zdrowotne, wypadkowe oraz odpowiedzialności cywilnej. Wszystkie składki są opłacane regularnie, a Ty otrzymujesz pełną dokumentację.',
  },
  {
    question: 'Co obejmuje wsparcie w ramach Gewerbe?',
    answer:
      'Pomagamy w całym procesie: założeniu Gewerbe, rejestracjach podatkowych, ubezpieczeniach, księgowości oraz wszystkich formalnościach biurokratycznych. Masz stałego opiekuna, który pomoże w każdej sprawie.',
  },
  {
    question: 'Czy mam zapewnioną opiekę medyczną w Niemczech?',
    answer:
      'Tak, w ramach ubezpieczenia zdrowotnego masz dostęp do pełnej opieki medycznej w Niemczech. Pomożemy Ci w wyborze odpowiedniego ubezpieczyciela oraz wyjaśnimy wszystkie szczegóły.',
  },
  {
    question: 'Jak wygląda proces legalizacji pobytu i pracy?',
    answer:
      'Prowadzimy Cię krok po kroku przez cały proces: od rejestracji miejsca zamieszkania (Anmeldung), przez założenie Gewerbe, aż po wszystkie wymagane zgłoszenia. Zapewniamy wsparcie w języku polskim i niemieckim.',
  },
  {
    question: 'Jakie są koszty i co jest wliczone w cenę?',
    answer:
      'Koszt obejmuje: założenie Gewerbe, pierwsze konsultacje prawne, pomoc w rejestracjach, wybór ubezpieczenia oraz stałe wsparcie opiekuna. Dokładny cennik zostanie przedstawiony podczas pierwszej rozmowy.',
  },
];

export default function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  const toggleAccordion = (index: number) => {
    setOpenIndex(openIndex === index ? null : index);
  };

  return (
    <section className="py-20 px-4 bg-white">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-center text-[#1e3a8a] mb-4">
          Najczęściej zadawane pytania
        </h2>
        <p className="text-center text-gray-600 mb-12">
          Odpowiedzi na pytania, które najczęściej zadają nasi klienci
        </p>

        <div className="space-y-4">
          {faqData.map((item, index) => (
            <div
              key={index}
              className="border border-gray-200 rounded-lg overflow-hidden transition-all duration-300 hover:shadow-md"
            >
              <button
                onClick={() => toggleAccordion(index)}
                className="w-full text-left px-6 py-4 flex justify-between items-center bg-white hover:bg-gray-50 transition-colors"
              >
                <span className="font-semibold text-gray-800 pr-4">
                  {item.question}
                </span>
                <span
                  className={`text-[#1e3a8a] text-2xl font-bold transition-transform duration-300 flex-shrink-0 ${
                    openIndex === index ? 'rotate-180' : ''
                  }`}
                >
                  ▼
                </span>
              </button>

              <div
                className={`overflow-hidden transition-all duration-300 ${
                  openIndex === index ? 'max-h-96' : 'max-h-0'
                }`}
              >
                <div className="px-6 py-4 bg-gray-50 text-gray-700 border-t border-gray-200">
                  {item.answer}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
