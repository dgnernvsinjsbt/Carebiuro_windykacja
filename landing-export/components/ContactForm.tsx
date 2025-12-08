'use client';

import { useState } from 'react';
import { contactFormSchema, type ContactFormData } from '@/lib/validation';
import toast from 'react-hot-toast';

export default function ContactForm() {
  const [formData, setFormData] = useState<ContactFormData>({
    name: '',
    email: '',
    phone: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate form data
    const result = contactFormSchema.safeParse(formData);

    if (!result.success) {
      const firstError = result.error.errors[0];
      toast.error(firstError.message);
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await fetch('/api/contact', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(result.data),
      });

      if (!response.ok) {
        throw new Error('Nie udało się wysłać formularza');
      }

      toast.success('Dziękujemy! Wkrótce się z Tobą skontaktujemy.');

      // Reset form
      setFormData({
        name: '',
        email: '',
        phone: '',
      });
    } catch (error) {
      toast.error('Wystąpił błąd. Spróbuj ponownie później.');
      console.error('Form submission error:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section id="contact" className="py-20 px-4 bg-gray-50">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-center text-[#1e3a8a] mb-4">
          Zapytaj o szczegóły
        </h2>
        <p className="text-center text-gray-600 mb-10">
          Wypełnij formularz, a nasz konsultant skontaktuje się z Tobą w ciągu 24 godzin
        </p>

        <form
          onSubmit={handleSubmit}
          className="bg-white rounded-lg shadow-lg p-8 md:p-10"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            {/* Name field */}
            <div>
              <label
                htmlFor="name"
                className="block text-sm font-semibold text-gray-700 mb-2"
              >
                Imię i nazwisko
              </label>
              <input
                type="text"
                id="name"
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1e3a8a] focus:border-transparent transition-all"
                placeholder="Jan Kowalski"
                required
              />
            </div>

            {/* Email field */}
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-semibold text-gray-700 mb-2"
              >
                Email
              </label>
              <input
                type="email"
                id="email"
                value={formData.email}
                onChange={(e) =>
                  setFormData({ ...formData, email: e.target.value })
                }
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1e3a8a] focus:border-transparent transition-all"
                placeholder="jan@example.com"
                required
              />
            </div>
          </div>

          {/* Phone field - full width */}
          <div className="mb-8">
            <label
              htmlFor="phone"
              className="block text-sm font-semibold text-gray-700 mb-2"
            >
              Numer telefonu
            </label>
            <input
              type="tel"
              id="phone"
              value={formData.phone}
              onChange={(e) =>
                setFormData({ ...formData, phone: e.target.value })
              }
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1e3a8a] focus:border-transparent transition-all"
              placeholder="+48 123 456 789"
              required
            />
          </div>

          {/* Submit button */}
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-[#ca8a04] hover:bg-[#a16207] text-white font-bold py-4 px-6 rounded-lg transition-all duration-300 transform hover:scale-[1.02] shadow-md disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
          >
            {isSubmitting ? 'Wysyłanie...' : 'Wyślij zapytanie'}
          </button>
        </form>
      </div>
    </section>
  );
}
