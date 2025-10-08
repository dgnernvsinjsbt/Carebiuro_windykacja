'use client';

import { useState } from 'react';
import toast from 'react-hot-toast';
import { FiscalSyncData } from '@/types';

interface ProgressiveReminderButtonsProps {
  invoiceId: number;
  fiscalSync: FiscalSyncData | null;
  disabled: boolean;
  clientPhone?: string;
  windykacjaEnabled: boolean;
}

export default function ProgressiveReminderButtons({
  invoiceId,
  fiscalSync,
  disabled,
  clientPhone,
  windykacjaEnabled,
}: ProgressiveReminderButtonsProps) {
  const [sending, setSending] = useState<string | null>(null);

  const sendReminder = async (
    type: 'email' | 'sms' | 'whatsapp',
    level: 1 | 2 | 3
  ) => {
    const key = `${type}_${level}`;
    setSending(key);

    const toastId = toast.loading(
      `Wysyłanie ${type.toUpperCase()} ${level}...`
    );

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
        toast.success(`Wysłano ${type.toUpperCase()} ${level}`, {
          id: toastId,
        });
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

  // Check if a button should be enabled
  const isButtonEnabled = (
    type: 'email' | 'sms' | 'whatsapp',
    level: 1 | 2 | 3
  ): boolean => {
    if (!windykacjaEnabled) return false; // WINDYKACJA is OFF
    if (disabled) return false; // STOP is ON

    // SMS and WhatsApp require phone number
    if ((type === 'sms' || type === 'whatsapp') && !clientPhone) {
      return false;
    }

    if (!fiscalSync) return level === 1; // No data yet, only level 1 available

    const typeUpper = type.toUpperCase() as 'EMAIL' | 'SMS' | 'WHATSAPP';

    // Level 1 is always available
    if (level === 1) {
      return !fiscalSync[`${typeUpper}_1` as keyof FiscalSyncData];
    }

    // Level 2 requires level 1 to be sent
    if (level === 2) {
      const level1Sent = fiscalSync[`${typeUpper}_1` as keyof FiscalSyncData];
      const level2Sent = fiscalSync[`${typeUpper}_2` as keyof FiscalSyncData];
      return level1Sent && !level2Sent;
    }

    // Level 3 requires level 2 to be sent
    if (level === 3) {
      const level2Sent = fiscalSync[`${typeUpper}_2` as keyof FiscalSyncData];
      const level3Sent = fiscalSync[`${typeUpper}_3` as keyof FiscalSyncData];
      return level2Sent && !level3Sent;
    }

    return false;
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
    const fieldName =
      `${type.toUpperCase()}_${level}` as keyof FiscalSyncData;
    const alreadySent = fiscalSync?.[fieldName] === true;
    const isEnabled = isButtonEnabled(type, level);
    const isDisabled = !isEnabled || sending !== null;

    // Check if phone is missing for SMS/WhatsApp
    const noPhone = (type === 'sms' || type === 'whatsapp') && !clientPhone;

    // Hide button if already sent
    if (alreadySent) {
      return null;
    }

    return (
      <button
        onClick={() => sendReminder(type, level)}
        disabled={isDisabled}
        className={`
          px-2 py-1 text-xs font-medium rounded transition-colors
          ${
            isEnabled
              ? `${color} text-white hover:opacity-80`
              : 'bg-gray-200 text-gray-400 cursor-not-allowed'
          }
        `}
        title={
          !windykacjaEnabled
            ? 'Windykacja wyłączona - włącz windykację w profilu klienta'
            : disabled
            ? 'STOP włączony'
            : noPhone
            ? 'Brak numeru telefonu - nie można wysłać'
            : !isEnabled
            ? `Wyślij najpierw ${type.toUpperCase()} ${level - 1}`
            : `Wyślij ${label}`
        }
      >
        {label}
      </button>
    );
  };

  return (
    <div className="flex gap-1 flex-wrap">
      {/* Email buttons */}
      <ReminderButton
        type="email"
        level={1}
        label="E1"
        color="bg-blue-500"
      />
      <ReminderButton
        type="email"
        level={2}
        label="E2"
        color="bg-blue-600"
      />
      <ReminderButton
        type="email"
        level={3}
        label="E3"
        color="bg-blue-700"
      />

      {/* SMS buttons */}
      <ReminderButton type="sms" level={1} label="S1" color="bg-purple-500" />
      <ReminderButton type="sms" level={2} label="S2" color="bg-purple-600" />
      <ReminderButton type="sms" level={3} label="S3" color="bg-purple-700" />

      {/* WhatsApp buttons */}
      <ReminderButton
        type="whatsapp"
        level={1}
        label="W1"
        color="bg-green-500"
      />
      <ReminderButton
        type="whatsapp"
        level={2}
        label="W2"
        color="bg-green-600"
      />
      <ReminderButton
        type="whatsapp"
        level={3}
        label="W3"
        color="bg-green-700"
      />
    </div>
  );
}
