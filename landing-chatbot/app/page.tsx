'use client';

import React, { useState } from 'react';
import { Play, Shield, CheckCircle, Lock, MessageCircle, ChevronDown, ChevronUp } from 'lucide-react';
import toast from 'react-hot-toast';

export default function LandingPage() {
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: ''
  });

  const toggleFaq = (index: number) => {
    setOpenFaq(openFaq === index ? null : index);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      const response = await fetch('/api/contact', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        throw new Error('Failed to submit form');
      }

      toast.success('Dziękujemy! Skontaktujemy się wkrótce.', {
        duration: 5000,
        icon: '✅',
      });

      setFormData({ name: '', email: '', phone: '' });
    } catch (error) {
      toast.error('Coś poszło nie tak. Spróbuj ponownie.', {
        duration: 5000,
        icon: '❌',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const faqs = [
    {
      question: "Co to jest Gewerbe i czy muszę mieć meldunek?",
      answer: "Gewerbe to niemiecka działalność gospodarcza. Aby ją założyć, potrzebujesz adresu w Niemczech. Jeśli nie masz meldunku, nasze biuro (Carebiuro / CBB-OFFICE GMBH) udostępnia adres niezbędny do rejestracji i odbiera Twoją korespondencję."
    },
    {
      question: "Jak wygląda proces rejestracji?",
      answer: "Proces jest maksymalnie uproszczony. Napisz do nas e-mail, a otrzymasz komplet dokumentów. Wszystko odbywa się zdalnie, bez potrzeby jeżdżenia po urzędach. Często rejestrację zamykamy w ciągu 24 godzin."
    },
    {
      question: "Czy pomagacie w prowadzeniu firmy po rejestracji?",
      answer: "Tak. Oferujemy kompleksową obsługę: wsparcie w korespondencji z urzędami, pomoc w wystawianiu rachunków oraz pełną księgowość i rozliczenia podatkowe realizowane przez naszą firmę z pełnymi uprawnieniami niemieckimi."
    },
    {
      question: "Dlaczego warto wybrać wasze biuro?",
      answer: "Mamy 10 lat doświadczenia i należymy do najstarszych firm na rynku. Oferujemy wszystko 'z jednej ręki': Gewerbe, ubezpieczenie, rozliczenie podatkowe i adres. Twój rachunek może być zamówiony w 5 minut."
    }
  ];

  return (
    <div className="min-h-screen font-sans text-slate-800 py-10 px-4 overflow-x-hidden relative" style={{background: 'linear-gradient(135deg, #F5F0E8 0%, #EDE6DB 25%, #E8DFD3 50%, #DDD5C8 75%, #E5DED4 100%)'}}><div className="absolute inset-0 opacity-40" style={{background: 'radial-gradient(ellipse at 20% 20%, rgba(198,164,104,0.15) 0%, transparent 50%), radial-gradient(ellipse at 80% 80%, rgba(15,38,69,0.08) 0%, transparent 50%), radial-gradient(ellipse at 60% 30%, rgba(198,164,104,0.1) 0%, transparent 40%)'}}></div>

      {/* MAIN CARD CONTAINER */}
      <main className="max-w-[1000px] mx-auto bg-white shadow-[0_30px_60px_-15px_rgba(0,0,0,0.3)] rounded-[30px] overflow-visible relative z-10">

        {/* --- HERO SECTION --- */}
        <div className="relative p-6 pt-10 pb-20 md:p-16 text-white text-center overflow-hidden rounded-t-[30px] bg-[#0F2645]">

          {/* 1. TŁO - GRADIENT */}
          <div className="absolute inset-0 bg-gradient-to-br from-[#1a3b66] via-[#0F2645] to-[#0a1a30] z-0"></div>

          {/* 2. TŁO - DUSZKI (Ikony rysowane kodem) */}
          <Lock className="absolute top-[-20px] -right-20 w-96 h-96 text-white opacity-[0.03] rotate-12 pointer-events-none z-0" strokeWidth={1} />
          <Shield className="absolute bottom-[-50px] -left-20 w-[400px] h-[400px] text-white opacity-[0.03] -rotate-12 pointer-events-none z-0" strokeWidth={1} />
          <div className="absolute top-40 left-10 opacity-[0.1] rotate-[-15deg] pointer-events-none hidden md:block">
             <div className="relative">
                <div className="w-24 h-24 border-4 border-white rounded-full flex items-center justify-center border-dashed">
                    <CheckCircle className="w-12 h-12 text-white" />
                </div>
             </div>
          </div>
           <div className="absolute top-60 right-10 opacity-[0.1] rotate-[15deg] pointer-events-none hidden md:block">
              <Shield className="w-20 h-20 text-white fill-transparent stroke-2" />
              <CheckCircle className="w-8 h-8 text-white absolute bottom-0 right-0 fill-white stroke-[#0F2645]" />
          </div>

          {/* CONTENT HERO */}
          <div className="relative z-10 flex flex-col items-center">
            <h2 className="text-2xl md:text-[2.5rem] font-serif font-bold text-[#C6A468] mb-4 uppercase leading-tight drop-shadow-md">
              Legalna Działalność <br/> w Niemczech
            </h2>
            <p className="text-gray-200 mb-8 max-w-2xl mx-auto text-sm md:text-base font-medium leading-relaxed">
              Pełne ubezpieczenie zdrowotne i społeczne, legalna działalność <br className="hidden md:block"/> (Gewerbe) oraz wsparcie prawne.
            </p>

            {/* VIDEO FRAME - GOLD BORDER */}
            <div className="relative w-full max-w-3xl mx-auto mb-10 rounded-2xl border-[3px] border-[#C6A468] shadow-2xl overflow-hidden aspect-video group cursor-pointer bg-gray-900">
                <div className="w-full h-full bg-gradient-to-br from-gray-700 to-gray-900 opacity-70 group-hover:opacity-90 transition-opacity duration-500" />

                {/* Play Button */}
                <div className="absolute inset-0 flex items-center justify-center">
                   <div className="bg-black/40 backdrop-blur-sm w-20 h-20 rounded-full flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                      <Play fill="white" className="text-white ml-2 w-10 h-10" />
                   </div>
                </div>

                {/* Text Overlay on Video */}
                <div className="absolute bottom-8 left-0 right-0 flex justify-center px-4">
                  <div className="bg-[#5e5e5e]/60 backdrop-blur-sm border border-white/40 px-6 py-3 rounded text-sm md:text-lg text-white uppercase tracking-wider font-serif text-center">
                    Obejrzyj wideo o Twoim <br/> bezpieczeństwie
                  </div>
                </div>
            </div>

            {/* Button */}
            <a
              href="#formularz"
              className="bg-[#C6A468] hover:bg-[#b08d55] text-white font-bold py-4 px-12 rounded-full shadow-lg transition-transform transform hover:-translate-y-0.5 uppercase tracking-widest text-sm md:text-base"
            >
              Zapytaj o szczegóły
            </a>
          </div>
        </div>

        {/* --- FORM SECTION --- */}
        <div id="formularz" className="bg-[#EFF4F8] py-16 px-6 md:px-24 text-center relative border-b border-gray-200 scroll-mt-4">

           {/* DIVIDER ICON (SHIELD WITH LOCK) */}
           <div className="absolute -top-10 left-1/2 transform -translate-x-1/2 z-20">
              <div className="relative">
                 <Shield className="w-20 h-20 text-[#C6A468]" fill="#C6A468" strokeWidth={0} />
                 <Lock className="w-8 h-8 text-[#0F2645] absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 fill-[#0F2645]" />
              </div>
           </div>

           <h3 className="text-2xl font-serif font-bold text-[#0F2645] mt-4 mb-8 uppercase tracking-wide">
             Zapytaj o Szczegóły
           </h3>

           <form onSubmit={handleSubmit} className="max-w-xl mx-auto space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <input
                  type="text"
                  placeholder="Imię i nazwisko"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                  disabled={isSubmitting}
                  className="w-full p-3 bg-white border-2 border-[#8daec4] rounded-md focus:border-[#0F2645] focus:outline-none placeholder-gray-500 font-medium disabled:opacity-50"
                />
                <input
                  type="email"
                  placeholder="E-mail"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  required
                  disabled={isSubmitting}
                  className="w-full p-3 bg-white border-2 border-[#8daec4] rounded-md focus:border-[#0F2645] focus:outline-none placeholder-gray-500 font-medium disabled:opacity-50"
                />
              </div>
              <input
                type="tel"
                placeholder="Numer telefonu"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                required
                disabled={isSubmitting}
                className="w-full p-3 bg-white border-2 border-[#8daec4] rounded-md focus:border-[#0F2645] focus:outline-none placeholder-gray-500 font-medium disabled:opacity-50"
              />

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full bg-[#C6A468] hover:bg-[#b08d55] text-white font-bold py-4 rounded-full shadow-md uppercase mt-6 tracking-wide text-sm md:text-base disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSubmitting ? 'Wysyłanie...' : 'Wyślij Zapytanie'}
              </button>
           </form>
        </div>

        {/* --- FAQ SECTION --- */}
        <div className="bg-white py-16 px-6 md:px-16 rounded-b-[30px]">
          <div className="text-center mb-10">
             <h3 className="text-2xl font-serif font-bold text-[#0F2645] uppercase tracking-wide">
               Najczęściej zadawane pytania
             </h3>
             <div className="w-full h-[1px] bg-gray-200 mt-6"></div>
          </div>

           <div className="space-y-0 max-w-4xl mx-auto">
            {faqs.map((faq, index) => (
              <div key={index} className="border-b border-gray-200 last:border-0">
                <button
                  onClick={() => toggleFaq(index)}
                  className="w-full flex justify-between items-start text-left focus:outline-none group py-5"
                >
                  <div className="flex items-start space-x-4">
                    <div className="mt-0.5 flex-shrink-0">
                      <Shield size={20} className="text-[#C6A468] fill-[#C6A468]"/>
                    </div>
                    <span className="font-bold text-[#0F2645] text-sm md:text-base leading-tight">
                      {faq.question}
                    </span>
                  </div>
                  {openFaq === index ? <ChevronUp size={20} className="text-gray-400 min-w-[20px]"/> : <ChevronDown size={20} className="text-gray-400 min-w-[20px]"/>}
                </button>
                {openFaq === index && (
                  <div className="mb-6 ml-10 text-gray-700 text-sm leading-relaxed">
                    {faq.answer}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* --- FOOTER --- */}
        <footer className="bg-[#0F2645] text-white py-6 px-8 rounded-b-[30px] -mt-6 relative z-0">
           <div className="flex flex-col md:flex-row justify-between items-center text-[10px] md:text-xs text-gray-300 pt-4 border-t border-gray-700/50">
               <div className="flex items-center gap-2 mb-2 md:mb-0">
                  <Shield size={14} className="text-[#C6A468]" fill="#C6A468"/>
                  <CheckCircle size={14} className="text-[#C6A468]" fill="#C6A468"/>
                  <Lock size={14} className="text-[#C6A468]" fill="#C6A468"/>
               </div>
              <div className="text-center md:text-left mb-2 md:mb-0">
                  <p>&copy; 2024 Twoje Bezpieczeństwo. Wszelkie prawa zastrzeżone.</p>
                  <p className="text-[#C6A468]">kontakt@twojebezpieczenstwo.pl</p>
              </div>
              <div className="flex flex-col md:items-end space-y-1">
                 <a href="#" className="hover:text-white">Polityka Prywatności</a>
                 <a href="#" className="hover:text-white">Regulamin</a>
                 <a href="#" className="hover:text-white">O Nas</a>
                 <a href="#" className="hover:text-white">Kontakt</a>
              </div>
           </div>
        </footer>

      </main>
    </div>
  );
}
