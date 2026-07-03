import Link from "next/link";
import { Cpu, ArrowLeft } from "lucide-react";

export default function ModelsPage() {
  return (
    <div className="min-h-screen bg-space-900 text-slate-200 p-8">
      <nav className="mb-12">
        <Link href="/" className="inline-flex items-center gap-2 text-gray-400 hover:text-neon-blue transition-colors">
          <ArrowLeft className="w-5 h-5" /> Back to Home
        </Link>
      </nav>
      
      <main className="max-w-4xl mx-auto">
        <div className="flex items-center gap-4 mb-8">
          <Cpu className="w-10 h-10 text-neon-blue" />
          <h1 className="text-4xl font-extrabold text-white">AI Models Matrix</h1>
        </div>
        
        <div className="glass-panel p-8 rounded-3xl border border-white/10 text-center py-20">
          <p className="text-gray-400 text-lg mb-6">Model version tracking and Explainability Heatmaps are currently in development.</p>
          <div className="w-16 h-16 border-4 border-neon-blue/20 border-t-neon-blue rounded-full animate-spin mx-auto" />
        </div>
      </main>
    </div>
  );
}
