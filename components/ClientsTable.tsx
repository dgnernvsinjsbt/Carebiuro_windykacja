'use client';

import { useState, useMemo, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Client } from '@/types';
import { parseWindykacja } from '@/lib/windykacja-parser';
import WindykacjaToggle from './WindykacjaToggle';

// Warm cache on component mount
if (typeof window !== 'undefined') {
  setTimeout(() => {
    fetch('/', { method: 'HEAD' }).catch(() => {});
  }, 100);
}

interface ClientsTableProps {
  clients: Client[];
}

type SortField = 'name' | 'saldo' | 'invoices';
type SortDirection = 'asc' | 'desc';

export default function ClientsTable({ clients }: ClientsTableProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState<SortField>('name');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const router = useRouter();

  // Filter states
  const [showInvoiceFilter, setShowInvoiceFilter] = useState(false);
  const [showSaldoFilter, setShowSaldoFilter] = useState(false);
  const [showWindykacjaFilter, setShowWindykacjaFilter] = useState(false);
  const [windykacjaFilter, setWindykacjaFilter] = useState<'all' | 'enabled' | 'disabled'>('all');
  const [invoiceCountMin, setInvoiceCountMin] = useState<number | ''>('');
  const [invoiceCountMax, setInvoiceCountMax] = useState<number | ''>('');
  const [saldoMin, setSaldoMin] = useState<number | ''>('');
  const [saldoMax, setSaldoMax] = useState<number | ''>('');
  const [invoiceRangeError, setInvoiceRangeError] = useState(false);
  const [saldoRangeError, setSaldoRangeError] = useState(false);

  // Pagination states
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(50);

  // Filter and sort clients
  const filteredAndSortedClients = useMemo(() => {
    // Filter first
    const filtered = clients.filter((client) => {
      // Search query filter
      const query = searchQuery.toLowerCase();
      const matchesSearch =
        client.name?.toLowerCase().includes(query) ||
        client.id.toString().includes(query);

      if (!matchesSearch) return false;

      // Invoice count filter (only apply if range is valid)
      const invoiceCount = client.invoice_count || 0;
      const validInvoiceRange =
        invoiceCountMin === '' ||
        invoiceCountMax === '' ||
        invoiceCountMin <= invoiceCountMax;

      if (validInvoiceRange) {
        if (invoiceCountMin !== '' && invoiceCount < invoiceCountMin) return false;
        if (invoiceCountMax !== '' && invoiceCount > invoiceCountMax) return false;
      }

      // Saldo filter (only apply if range is valid)
      const saldo = client.total_unpaid || 0;
      const validSaldoRange =
        saldoMin === '' ||
        saldoMax === '' ||
        saldoMin <= saldoMax;

      if (validSaldoRange) {
        if (saldoMin !== '' && saldo < saldoMin) return false;
        if (saldoMax !== '' && saldo > saldoMax) return false;
      }

      // Windykacja filter
      if (windykacjaFilter !== 'all') {
        const windykacjaEnabled = parseWindykacja(client.note);
        if (windykacjaFilter === 'enabled' && !windykacjaEnabled) return false;
        if (windykacjaFilter === 'disabled' && windykacjaEnabled) return false;
      }

      return true;
    });

    // Then sort
    return [...filtered].sort((a, b) => {
      let compareValue = 0;

      if (sortField === 'name') {
        const nameA = (a.name || '').toLowerCase();
        const nameB = (b.name || '').toLowerCase();
        compareValue = nameA.localeCompare(nameB);
      } else if (sortField === 'saldo') {
        compareValue = (a.total_unpaid || 0) - (b.total_unpaid || 0);
      } else if (sortField === 'invoices') {
        compareValue = (a.invoice_count || 0) - (b.invoice_count || 0);
      }

      return sortDirection === 'asc' ? compareValue : -compareValue;
    });
  }, [clients, searchQuery, sortField, sortDirection, invoiceCountMin, invoiceCountMax, saldoMin, saldoMax, windykacjaFilter]);

  // Paginate clients
  const paginatedClients = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    return filteredAndSortedClients.slice(startIndex, endIndex);
  }, [filteredAndSortedClients, currentPage, itemsPerPage]);

  const totalPages = Math.ceil(filteredAndSortedClients.length / itemsPerPage);

  // Reset to page 1 when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, invoiceCountMin, invoiceCountMax, saldoMin, saldoMax, windykacjaFilter, itemsPerPage]);

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  // Validate filter ranges
  useEffect(() => {
    if (invoiceCountMin !== '' && invoiceCountMax !== '' && invoiceCountMin > invoiceCountMax) {
      setInvoiceRangeError(true);
    } else {
      setInvoiceRangeError(false);
    }
  }, [invoiceCountMin, invoiceCountMax]);

  useEffect(() => {
    if (saldoMin !== '' && saldoMax !== '' && saldoMin > saldoMax) {
      setSaldoRangeError(true);
    } else {
      setSaldoRangeError(false);
    }
  }, [saldoMin, saldoMax]);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (!target.closest('.filter-dropdown')) {
        setShowInvoiceFilter(false);
        setShowSaldoFilter(false);
        setShowWindykacjaFilter(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Search and pagination controls */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between gap-4">
          <div className="relative flex-1">
            <input
              type="text"
              placeholder="Szukaj klientów..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-4 py-2 pl-10 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
            />
            <svg
              className="absolute left-3 top-2.5 w-5 h-5 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-600 whitespace-nowrap">Pokaż:</label>
              <select
                value={itemsPerPage}
                onChange={(e) => setItemsPerPage(Number(e.target.value))}
                className="px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-teal-500"
              >
                <option value={10}>10</option>
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
                <option value={250}>250</option>
                <option value={1000}>1000</option>
              </select>
            </div>

            {totalPages > 1 && (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage(1)}
                  disabled={currentPage === 1}
                  className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  «
                </button>
                <button
                  onClick={() => setCurrentPage(currentPage - 1)}
                  disabled={currentPage === 1}
                  className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  ‹
                </button>
                <span className="text-sm text-gray-600 whitespace-nowrap">
                  Strona {currentPage} z {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage(currentPage + 1)}
                  disabled={currentPage === totalPages}
                  className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  ›
                </button>
                <button
                  onClick={() => setCurrentPage(totalPages)}
                  disabled={currentPage === totalPages}
                  className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  »
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 table-fixed">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-[55%]">
                <button
                  onClick={() => toggleSort('name')}
                  className="flex items-center gap-1 hover:text-gray-700 transition-colors"
                  title={`Sortuj ${sortField === 'name' && sortDirection === 'desc' ? 'rosnąco' : 'malejąco'}`}
                >
                  Imię i nazwisko / Nazwa
                  {sortField === 'name' && (
                    <span className="text-xs">
                      {sortDirection === 'asc' ? '↑' : '↓'}
                    </span>
                  )}
                </button>
              </th>
              <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider w-[15%]">
                <div className="flex items-center justify-center gap-2">
                  <span>Windykacja</span>
                  <div className="relative filter-dropdown">
                    <button
                      onClick={() => setShowWindykacjaFilter(!showWindykacjaFilter)}
                      className={`p-1 rounded hover:bg-gray-200 transition-colors ${
                        windykacjaFilter !== 'all' ? 'text-teal-600' : 'text-gray-400'
                      }`}
                      title="Filtruj"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                      </svg>
                    </button>
                    {showWindykacjaFilter && (
                      <div className="absolute top-full right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg p-3 z-[100] min-w-[180px]">
                        <div className="text-xs font-semibold text-gray-700 mb-2">Status windykacji</div>
                        <div className="space-y-1">
                          <label className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-1 rounded">
                            <input
                              type="radio"
                              name="windykacja"
                              value="all"
                              checked={windykacjaFilter === 'all'}
                              onChange={(e) => setWindykacjaFilter(e.target.value as 'all')}
                              className="text-teal-600 focus:ring-teal-500"
                            />
                            <span className="text-xs">Wszyscy</span>
                          </label>
                          <label className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-1 rounded">
                            <input
                              type="radio"
                              name="windykacja"
                              value="enabled"
                              checked={windykacjaFilter === 'enabled'}
                              onChange={(e) => setWindykacjaFilter(e.target.value as 'enabled')}
                              className="text-teal-600 focus:ring-teal-500"
                            />
                            <span className="text-xs">Włączona</span>
                          </label>
                          <label className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-1 rounded">
                            <input
                              type="radio"
                              name="windykacja"
                              value="disabled"
                              checked={windykacjaFilter === 'disabled'}
                              onChange={(e) => setWindykacjaFilter(e.target.value as 'disabled')}
                              className="text-teal-600 focus:ring-teal-500"
                            />
                            <span className="text-xs">Wyłączona</span>
                          </label>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </th>
              <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider w-[15%]">
                <div className="flex items-center justify-center gap-2">
                  <button
                    onClick={() => toggleSort('invoices')}
                    className="flex items-center gap-1 hover:text-gray-700 transition-colors whitespace-nowrap"
                    title={`Sortuj ${sortField === 'invoices' && sortDirection === 'desc' ? 'rosnąco' : 'malejąco'}`}
                  >
                    Zaległe faktury
                    {sortField === 'invoices' && (
                      <span className="text-xs">
                        {sortDirection === 'asc' ? '↑' : '↓'}
                      </span>
                    )}
                  </button>
                  <div className="relative filter-dropdown">
                    <button
                      onClick={() => setShowInvoiceFilter(!showInvoiceFilter)}
                      className={`p-1 rounded hover:bg-gray-200 transition-colors ${
                        (invoiceCountMin !== '' || invoiceCountMax !== '') ? 'text-teal-600' : 'text-gray-400'
                      }`}
                      title="Filtruj"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                      </svg>
                    </button>
                    {showInvoiceFilter && (
                      <div className="absolute top-full right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg p-3 z-50 min-w-[200px]">
                        <div className="text-xs font-semibold text-gray-700 mb-2">Zakres ilości faktur</div>
                        <div className="space-y-2">
                          <div>
                            <label className="text-xs text-gray-600">Od:</label>
                            <input
                              type="number"
                              min="0"
                              value={invoiceCountMin}
                              onChange={(e) => setInvoiceCountMin(e.target.value === '' ? '' : Number(e.target.value))}
                              className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-teal-500"
                              placeholder="0"
                            />
                          </div>
                          <div>
                            <label className="text-xs text-gray-600">Do:</label>
                            <input
                              type="number"
                              min="0"
                              value={invoiceCountMax}
                              onChange={(e) => setInvoiceCountMax(e.target.value === '' ? '' : Number(e.target.value))}
                              className={`w-full px-2 py-1 text-sm border rounded focus:outline-none focus:ring-1 ${
                                invoiceRangeError
                                  ? 'border-red-300 focus:ring-red-500'
                                  : 'border-gray-300 focus:ring-teal-500'
                              }`}
                              placeholder="∞"
                            />
                          </div>
                          {invoiceRangeError && (
                            <div className="text-xs text-red-600 flex items-center gap-1">
                              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                              </svg>
                              "Od" nie może być większe niż "Do"
                            </div>
                          )}
                          <button
                            onClick={() => {
                              setInvoiceCountMin('');
                              setInvoiceCountMax('');
                            }}
                            className="w-full px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded transition-colors"
                          >
                            Wyczyść
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </th>
              <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider w-[15%]">
                <div className="flex items-center justify-end gap-2">
                  <button
                    onClick={() => toggleSort('saldo')}
                    className="flex items-center gap-1 hover:text-gray-700 transition-colors whitespace-nowrap"
                    title={`Sortuj ${sortField === 'saldo' && sortDirection === 'desc' ? 'rosnąco' : 'malejąco'}`}
                  >
                    Saldo nieopłacone
                    {sortField === 'saldo' && (
                      <span className="text-xs">
                        {sortDirection === 'asc' ? '↑' : '↓'}
                      </span>
                    )}
                  </button>
                  <div className="relative filter-dropdown">
                    <button
                      onClick={() => setShowSaldoFilter(!showSaldoFilter)}
                      className={`p-1 rounded hover:bg-gray-200 transition-colors ${
                        (saldoMin !== '' || saldoMax !== '') ? 'text-teal-600' : 'text-gray-400'
                      }`}
                      title="Filtruj"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                      </svg>
                    </button>
                    {showSaldoFilter && (
                      <div className="absolute top-full right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg p-3 z-50 min-w-[220px]">
                        <div className="text-xs font-semibold text-gray-700 mb-2">Zakres salda</div>
                        <div className="space-y-2">
                          <div>
                            <label className="text-xs text-gray-600">Od (€):</label>
                            <input
                              type="number"
                              min="0"
                              step="0.01"
                              value={saldoMin}
                              onChange={(e) => setSaldoMin(e.target.value === '' ? '' : Number(e.target.value))}
                              className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-teal-500"
                              placeholder="0.00"
                            />
                          </div>
                          <div>
                            <label className="text-xs text-gray-600">Do (€):</label>
                            <input
                              type="number"
                              min="0"
                              step="0.01"
                              value={saldoMax}
                              onChange={(e) => setSaldoMax(e.target.value === '' ? '' : Number(e.target.value))}
                              className={`w-full px-2 py-1 text-sm border rounded focus:outline-none focus:ring-1 ${
                                saldoRangeError
                                  ? 'border-red-300 focus:ring-red-500'
                                  : 'border-gray-300 focus:ring-teal-500'
                              }`}
                              placeholder="∞"
                            />
                          </div>
                          {saldoRangeError && (
                            <div className="text-xs text-red-600 flex items-center gap-1">
                              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                              </svg>
                              "Od" nie może być większe niż "Do"
                            </div>
                          )}
                          <button
                            onClick={() => {
                              setSaldoMin('');
                              setSaldoMax('');
                            }}
                            className="w-full px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded transition-colors"
                          >
                            Wyczyść
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {paginatedClients.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-6 py-8 text-center text-gray-500">
                  {searchQuery
                    ? 'Nie znaleziono klientów'
                    : 'Brak klientów. Uruchom synchronizację aby pobrać dane.'}
                </td>
              </tr>
            ) : (
              paginatedClients.map((client) => {
                const windykacjaEnabled = parseWindykacja(client.note);

                return (
                  <tr
                    key={client.id}
                    className="hover:bg-gray-50 transition-colors"
                  >
                    <td
                      className="px-4 py-2 cursor-pointer"
                      onClick={() => router.push(`/client/${client.id}`)}
                    >
                      <div className="text-sm font-medium text-gray-900">
                        {client.name || 'Brak nazwy'}
                      </div>
                      <div className="text-xs text-gray-500">ID: {client.id}</div>
                    </td>
                    <td className="px-4 py-2 text-center" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-center">
                        <WindykacjaToggle
                          clientId={client.id}
                          initialWindykacja={windykacjaEnabled}
                        />
                      </div>
                    </td>
                    <td
                      className="px-4 py-2 text-center cursor-pointer"
                      onClick={() => router.push(`/client/${client.id}`)}
                    >
                      <span className="text-sm text-gray-600">
                        {client.invoice_count || 0}
                      </span>
                    </td>
                    <td
                      className="px-4 py-2 text-right cursor-pointer"
                      onClick={() => router.push(`/client/${client.id}`)}
                    >
                      <span
                        className={`text-sm font-semibold ${
                          (client.total_unpaid || 0) > 0
                            ? 'text-red-600'
                            : 'text-green-600'
                        }`}
                      >
                        €{(client.total_unpaid || 0).toFixed(2)}
                      </span>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Footer with pagination */}
      <div className="px-6 py-3 border-t border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="text-sm text-gray-600">
              Pokazano {paginatedClients.length > 0 ? (currentPage - 1) * itemsPerPage + 1 : 0} - {Math.min(currentPage * itemsPerPage, filteredAndSortedClients.length)} z {filteredAndSortedClients.length} klientów
            </div>
            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-600">Pokaż:</label>
              <select
                value={itemsPerPage}
                onChange={(e) => setItemsPerPage(Number(e.target.value))}
                className="px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-teal-500"
              >
                <option value={10}>10</option>
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
                <option value={250}>250</option>
                <option value={1000}>1000</option>
              </select>
            </div>
          </div>

          {totalPages > 1 && (
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage(1)}
                disabled={currentPage === 1}
                className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                «
              </button>
              <button
                onClick={() => setCurrentPage(currentPage - 1)}
                disabled={currentPage === 1}
                className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                ‹
              </button>
              <span className="text-sm text-gray-600">
                Strona {currentPage} z {totalPages}
              </span>
              <button
                onClick={() => setCurrentPage(currentPage + 1)}
                disabled={currentPage === totalPages}
                className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                ›
              </button>
              <button
                onClick={() => setCurrentPage(totalPages)}
                disabled={currentPage === totalPages}
                className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                »
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
