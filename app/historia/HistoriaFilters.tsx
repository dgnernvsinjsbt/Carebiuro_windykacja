'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';

interface HistoriaFiltersProps {
  currentStartDate: string;
  currentEndDate: string;
  currentType: string;
}

export default function HistoriaFilters({
  currentStartDate,
  currentEndDate,
  currentType,
}: HistoriaFiltersProps) {
  const router = useRouter();
  const [startDate, setStartDate] = useState(currentStartDate);
  const [endDate, setEndDate] = useState(currentEndDate);
  const [selectedType, setSelectedType] = useState(currentType);

  const applyFilters = () => {
    // Navigate with new params - this triggers a full server re-render
    const params = new URLSearchParams({
      startDate,
      endDate,
      type: selectedType,
      _t: String(Date.now()), // Cache buster
    });
    router.push(`/historia?${params}`);
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 mb-6">
      <div className="flex flex-wrap items-end gap-4">
        <div className="flex-1 min-w-[150px]">
          <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5">Data od</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
          />
        </div>
        <div className="flex-1 min-w-[150px]">
          <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5">Data do</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
          />
        </div>
        <div className="flex-1 min-w-[150px]">
          <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5">Typ wiadomości</label>
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
          >
            <option value="all">Wszystkie</option>
            <option value="email">Email</option>
            <option value="sms">SMS</option>
            <option value="whatsapp">WhatsApp</option>
          </select>
        </div>
        <button
          onClick={applyFilters}
          className="px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium text-sm whitespace-nowrap"
        >
          Zastosuj
        </button>
      </div>
    </div>
  );
}
