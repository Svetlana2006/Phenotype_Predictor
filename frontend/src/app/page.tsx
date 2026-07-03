import Link from 'next/link';

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-8 relative overflow-hidden">
      {/* Abstract Background Glows */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-neon-blue/20 rounded-full blur-[120px] -z-10 pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-blue-600/10 rounded-full blur-[150px] -z-10 pointer-events-none" />

      {/* Main Glass Hero Panel */}
      <div className="glass-panel rounded-3xl p-12 max-w-4xl w-full text-center relative overflow-hidden group">
        {/* Animated top border glow */}
        <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-neon-blue to-transparent opacity-50 group-hover:opacity-100 transition-opacity duration-700" />
        
        <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight mb-6 text-white">
          Phenotype <span className="text-neon-blue text-glow">Predictor</span>
        </h1>
        
        <p className="text-lg md:text-xl text-gray-400 mb-10 max-w-2xl mx-auto leading-relaxed">
          The ultimate multi-task AI fusion engine. Predict age, ancestry, and pigmentation traits seamlessly from a single DNA sample.
        </p>

        <div className="flex flex-col sm:flex-row gap-6 justify-center items-center">
          <Link 
            href="/dashboard"
            className="group relative px-8 py-4 bg-neon-blue text-space-900 font-bold rounded-full overflow-hidden transition-all hover:scale-105"
          >
            <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300 ease-out" />
            <span className="relative z-10 flex items-center gap-2">
              Launch Fusion Engine
              <svg className="w-5 h-5 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </span>
          </Link>
          
          <Link 
            href="/models"
            className="px-8 py-4 glass-panel border-white/10 hover:border-neon-blue/50 text-white font-medium rounded-full transition-all hover:text-neon-blue"
          >
            View AI Models
          </Link>
        </div>
      </div>

      {/* Stats row below hero */}
      <div className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-6 w-full max-w-4xl text-center z-10">
        {[
          { label: 'Neural Core', value: 'Active' },
          { label: 'Models Loaded', value: '10' },
          { label: 'Feature Space', value: '10,000+' },
          { label: 'Prediction Mode', value: 'Multi-Task' },
        ].map((stat, i) => (
          <div key={i} className="glass-panel p-6 rounded-2xl border border-white/5 hover:border-neon-blue/30 transition-colors">
            <div className="text-neon-blue font-bold text-2xl mb-1 text-glow">{stat.value}</div>
            <div className="text-gray-500 text-xs uppercase tracking-wider font-semibold">{stat.label}</div>
          </div>
        ))}
      </div>
    </main>
  );
}
