import { z } from 'zod';

export const contactFormSchema = z.object({
  name: z.string().min(2, 'Imię i nazwisko musi mieć przynajmniej 2 znaki'),
  email: z.string().email('Nieprawidłowy adres email'),
  phone: z.string().min(9, 'Numer telefonu musi mieć przynajmniej 9 cyfr'),
});

export type ContactFormData = z.infer<typeof contactFormSchema>;
