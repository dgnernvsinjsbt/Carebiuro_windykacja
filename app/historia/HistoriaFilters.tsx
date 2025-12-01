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
    <div className="bg-white rounded-lg shadow p-6 mb-8">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Data od</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Data do</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Typ wiadomości</label>
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">Wszystkie</option>
            <option value="email">Email</option>
            <option value="sms">SMS</option>
            <option value="whatsapp">WhatsApp</option>
          </select>
        </div>
        <div className="flex items-end">
          <button
            onClick={applyFilters}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            Zastosuj filtry
          </button>
        </div>
      </div>
    </div>
  );
}
