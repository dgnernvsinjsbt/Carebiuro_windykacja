'use client';

import { useState } from 'react';
import toast from 'react-hot-toast';
import { FiscalSyncData } from '@/types';

interface ReminderButtonsProps {
  invoiceId: number;
  fiscalSync: FiscalSyncData | null;
  disabled: boolean;
}

export default function ReminderButtons({
  invoiceId,
  fiscalSync,
  disabled,
}: ReminderButtonsProps) {
  const [sending, setSending] = useState<string | null>(null);

  const sendReminder = async (type: 'email' | 'sms' | 'whatsapp', level: 1 | 2 | 3) => {
    const key = `${sending}`;
    setSending(key);

    const toastId = toast.loading(`Wysyłanie ${type.toUpperCase()} ${level}...`);

    try {
      const response = await fetch('/api/reminder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          invoice_id: invoiceId,
          type,
          level: level.toString(),
        }),
      });

      const data = await response.json();

      if (data.success) {
        toast.success(`Wysłano ${type.toUpperCase()} ${level}`, { id: toastId });
        // Refresh page to update UI
        setTimeout(() => window.location.reload(), 1000);
      } else {
        toast.error(`Błąd: ${data.error}`, { id: toastId });
      }
    } catch (error: any) {
      toast.error(`Błąd połączenia: ${error.message}`, { id: toastId });
    } finally {
      setSending(null);
    }
  };

  const ReminderButton = ({
    type,
    level,
    label,
    color,
  }: {
    type: 'email' | 'sms' | 'whatsapp';
    level: 1 | 2 | 3;
    label: string;
    color: string;
  }) => {
    const fieldName = `${type.toUpperCase()}_${level}` as keyof FiscalSyncData;
    const alreadySent = fiscalSync?.[fieldName] === true;
    const isDisabled = disabled || alreadySent || sending !== null;

    return (
      <button
        onClick={() => sendReminder(type, level)}
        disabled={isDisabled}
        className={`
          px-2 py-1 text-xs font-medium rounded transition-colors
          ${
            alreadySent
              ? 'bg-gray-100 text-gray-400 cursor-not-allowed line-through'
              : isDisabled
              ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
              : `${color} text-white hover:opacity-80`
          }
        `}
        title={alreadySent ? 'Już wysłane' : disabled ? 'STOP włączony' : `Wyślij ${label}`}
      >
        {label}
      </button>
    );
  };

  return (
    <div className="space-y-2">
      {/* Email buttons */}
      <div className="flex gap-1">
        <ReminderButton type="email" level={1} label="E1" color="bg-blue-500" />
        <ReminderButton type="email" level={2} label="E2" color="bg-blue-600" />
        <ReminderButton type="email" level={3} label="E3" color="bg-blue-700" />
      </div>

      {/* SMS buttons */}
      <div className="flex gap-1">
        <ReminderButton type="sms" level={1} label="S1" color="bg-green-500" />
        <ReminderButton type="sms" level={2} label="S2" color="bg-green-600" />
        <ReminderButton type="sms" level={3} label="S3" color="bg-green-700" />
      </div>

      {/* WhatsApp buttons */}
      <div className="flex gap-1">
        <ReminderButton type="whatsapp" level={1} label="W1" color="bg-purple-500" />
        <ReminderButton type="whatsapp" level={2} label="W2" color="bg-purple-600" />
        <ReminderButton type="whatsapp" level={3} label="W3" color="bg-purple-700" />
      </div>
    </div>
  );
}
