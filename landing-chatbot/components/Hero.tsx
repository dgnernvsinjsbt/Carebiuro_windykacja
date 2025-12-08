export default function Hero() {
  return (
    <section className="relative bg-gradient-to-br from-[#1e3a8a] to-[#0f172a] text-white py-20 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-6xl font-bold mb-4">
            TWOJE BEZPIECZEŃSTWO
          </h1>
          <p className="text-xl md:text-2xl mb-2 font-semibold">
            Polish Caregivers Germany
          </p>
          <p className="text-lg md:text-xl text-blue-200 mb-8">
            Legalne i pewne zatrudnienie w Niemczech
          </p>
        </div>

        {/* Video Placeholder */}
        <div className="max-w-4xl mx-auto mb-10">
          <div className="relative aspect-video bg-blue-900/50 rounded-lg border-2 border-blue-400/30 flex items-center justify-center">
            <div className="text-center">
              <div className="text-6xl mb-4">▶️</div>
              <p className="text-lg text-blue-200">Video Placeholder</p>
              <p className="text-sm text-blue-300 mt-2">
                Tutaj będzie wideo prezentujące usługi
              </p>
            </div>
          </div>
        </div>

        {/* CTA Button */}
        <div className="text-center">
          <a
            href="#contact"
            className="inline-block bg-[#ca8a04] hover:bg-[#a16207] text-white font-bold py-4 px-8 rounded-lg text-lg transition-all duration-300 transform hover:scale-105 shadow-lg"
          >
            Sprawdź oferty pracy
          </a>
        </div>
      </div>
    </section>
  );
}
