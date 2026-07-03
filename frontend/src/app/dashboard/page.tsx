"use client";

import { useState } from "react";
import { Upload, FileType, Activity, Search, ShieldAlert, Cpu, Copy, Download } from "lucide-react";

interface PredictionResult {
  sample_id: string;
  predictions: {
    age: {
      estimate: number | null;
      range: [number, number] | null;
    };
  };
  hard_labels: {
    ancestry: string;
    eye_color: string;
    hair_color: string;
    skin_color: string;
  };
}

export default function Dashboard() {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<PredictionResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setIsDragging(true);
    } else if (e.type === "dragleave") {
      setIsDragging(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const runPrediction = async () => {
    if (!file) return;
    setIsLoading(true);
    setError(null);
    
    try {
      // 1. Auto-login or register a default testing account to get a JWT
      const loginParams = new URLSearchParams();
      loginParams.append("username", "test@phenotype.com");
      loginParams.append("password", "password123");
      
      let authRes = await fetch("http://localhost:8000/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: loginParams
      });

      if (!authRes.ok) {
        // Register it if it doesn't exist
        await fetch("http://localhost:8000/api/v1/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: "test@phenotype.com", password: "password123", role: "researcher" })
        });
        
        // Try login again
        authRes = await fetch("http://localhost:8000/api/v1/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: loginParams
        });
      }

      const authData = await authRes.json();
      const token = authData.access_token;

      // 2. Run the actual prediction against your FastAPI backend
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch("http://localhost:8000/api/v1/predict", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`
        },
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Prediction failed");
      }

      const data = await res.json();
      setResults(data.samples); // The real array of ALL processed rows!
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(String(err));
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopy = () => {
    if (!results) return;
    const headers = "Sample ID\tAge\tAncestry\tEye Color\tHair Color\tSkin Color";
    const rows = results.map((r: PredictionResult) => 
      `${r.sample_id}\t${r.predictions.age.estimate !== null ? r.predictions.age.estimate.toFixed(1) : 'N/A'}\t${r.hard_labels.ancestry}\t${r.hard_labels.eye_color}\t${r.hard_labels.hair_color}\t${r.hard_labels.skin_color}`
    ).join("\n");
    navigator.clipboard.writeText(`${headers}\n${rows}`);
    alert("Copied to clipboard!");
  };

  const handleDownload = () => {
    if (!results) return;
    const headers = "Sample ID,Age,Ancestry,Eye Color,Hair Color,Skin Color\n";
    const rows = results.map((r: PredictionResult) => 
      `${r.sample_id},${r.predictions.age.estimate !== null ? r.predictions.age.estimate.toFixed(1) : 'N/A'},${r.hard_labels.ancestry},${r.hard_labels.eye_color},${r.hard_labels.hair_color},${r.hard_labels.skin_color}`
    ).join("\n");
    const blob = new Blob([headers + rows], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.setAttribute('hidden', '');
    a.setAttribute('href', url);
    a.setAttribute('download', 'phenotype_predictions.csv');
    document.body.appendChild(a);
    a.click();
    a.click();
    document.body.removeChild(a);
  };

  const handleDownloadSample = () => {
    const headers = "SampleID,rs12913832,rs16891982,cg00000029,cg00000030\n";
    const rows = "Demo_Sample_1,2,0,0.85,0.12\nDemo_Sample_2,0,2,0.10,0.95";
    const blob = new Blob([headers + rows], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.setAttribute('href', url);
    a.setAttribute('download', 'phenotype_template.csv');
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return (
    <div className="min-h-screen bg-space-900 text-slate-200">
      <nav className="glass-panel border-b border-white/5 px-8 py-4 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <Cpu className="w-8 h-8 text-neon-blue" />
          <span className="font-bold text-xl tracking-wide text-white">Phenotype<span className="text-neon-blue">Predictor</span></span>
        </div>
        <div className="flex items-center gap-2 text-sm font-medium text-emerald-400 bg-emerald-400/10 px-3 py-1.5 rounded-full border border-emerald-400/20">
          <Activity className="w-4 h-4" /> API Connected
        </div>
      </nav>

      <main className="max-w-7xl mx-auto p-8 py-12">
        {!results && (
          <div className="mb-10">
            <h1 className="text-4xl font-extrabold text-white mb-2">Fusion Engine Dashboard</h1>
            <p className="text-gray-400">Upload a genomic CSV file containing one or more sequences to predict traits.</p>
          </div>
        )}

        {!results ? (
          <div className="grid md:grid-cols-2 gap-10 items-start">
            {/* Upload Zone */}
            <div 
              className={`glass-panel border-2 border-dashed rounded-3xl p-12 text-center transition-all duration-300 ease-out flex flex-col items-center justify-center min-h-[400px]
                ${isDragging ? 'border-neon-blue bg-neon-blue/5 scale-[1.02]' : 'border-white/10 hover:border-neon-blue/50'}
              `}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              <input 
                type="file" 
                accept=".csv" 
                className="hidden" 
                id="file-upload" 
                onChange={handleFileSelect}
                onClick={(e) => { (e.target as HTMLInputElement).value = ''; }}
              />
              
              {!file ? (
                <>
                  <div className="w-24 h-24 rounded-full bg-neon-blue/10 flex items-center justify-center mb-6 text-neon-blue">
                    <Upload className="w-10 h-10" />
                  </div>
                  <h3 className="text-xl font-bold text-white mb-2">Initialize Sequence</h3>
                  <p className="text-gray-400 mb-8 max-w-xs mx-auto">Drag and drop your DNA .csv file here. We support both single-sequence and multi-sequence batches.</p>
                  
                  <div className="flex gap-4">
                    <button 
                      onClick={handleDownloadSample}
                      className="px-6 py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-full font-medium transition-colors text-sm"
                    >
                      Download Template
                    </button>
                    <label 
                      htmlFor="file-upload"
                      className="cursor-pointer px-6 py-3 bg-neon-blue hover:bg-neon-blue/90 text-space-900 border border-neon-blue rounded-full font-bold transition-colors text-sm"
                    >
                      Select File
                    </label>
                  </div>
                </>
              ) : (
                <>
                  <div className="w-24 h-24 rounded-full bg-emerald-500/10 flex items-center justify-center mb-6 text-emerald-400 animate-pulse">
                    <FileType className="w-10 h-10" />
                  </div>
                  <h3 className="text-xl font-bold text-white mb-2">{file.name}</h3>
                  <p className="text-gray-400 mb-8">{(file.size / 1024 / 1024).toFixed(2)} MB • Ready for processing</p>
                  
                  <div className="flex gap-4">
                    <button 
                      onClick={() => setFile(null)}
                      className="px-6 py-3 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 rounded-full font-medium transition-colors"
                    >
                      Cancel
                    </button>
                    <button 
                      onClick={runPrediction}
                      disabled={isLoading}
                      className="px-6 py-3 bg-neon-blue hover:bg-neon-blue/90 text-space-900 border border-neon-blue rounded-full font-bold transition-all disabled:opacity-50 flex items-center gap-2"
                    >
                      {isLoading ? (
                        <><Activity className="w-5 h-5 animate-spin" /> Processing Batch...</>
                      ) : (
                        <><Search className="w-5 h-5" /> Run Prediction</>
                      )}
                    </button>
                  </div>
                  {error && (
                    <div className="mt-6 p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 font-medium max-w-lg w-full break-words">
                      <ShieldAlert className="w-5 h-5 inline mr-2" />
                      {error}
                    </div>
                  )}
                </>
              )}
            </div>
            
            {/* Guidelines */}
            <div className="glass-panel p-8 rounded-3xl">
              <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-3">
                <ShieldAlert className="w-6 h-6 text-neon-blue" />
                Data Guidelines
              </h3>
              <ul className="space-y-4 text-gray-400">
                <li className="flex gap-3">
                  <div className="w-2 h-2 rounded-full bg-neon-blue mt-2 flex-shrink-0" />
                  <p>Input files must be in comma-separated values (.csv) format. Columns should be named with rsIDs (e.g. rs12913832) or CpG sites (e.g. cg00000029).</p>
                </li>
                <li className="flex gap-3">
                  <div className="w-2 h-2 rounded-full bg-neon-blue mt-2 flex-shrink-0" />
                  <p>Batch Processing: If your CSV contains multiple rows, the engine will automatically detect it (Max 50 sequences per upload).</p>
                </li>
                <li className="flex gap-3">
                  <div className="w-2 h-2 rounded-full bg-neon-blue mt-2 flex-shrink-0" />
                  <p>Missing Data? If you don't have certain SNPs or Epigenetic markers, leave the column blank or enter 0. The engine will gracefully skip traits it cannot predict.</p>
                </li>
              </ul>
            </div>
          </div>
        ) : (
          <div className="glass-panel p-10 rounded-3xl border border-neon-blue/20 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-neon-blue/5 rounded-full blur-[80px]" />
            <div className="flex justify-between items-center mb-8 relative z-10">
              <div>
                <h2 className="text-3xl font-extrabold text-white flex items-center gap-4">
                  <Activity className="w-8 h-8 text-neon-blue" />
                  Prediction Results
                </h2>
                <p className="text-gray-400 mt-2">Processed {results.length} sequence{results.length > 1 ? 's' : ''} successfully.</p>
              </div>
              
              <div className="flex items-center gap-4">
                {results.length > 1 && (
                  <>
                    <button onClick={handleCopy} className="px-4 py-2 flex items-center gap-2 bg-white/5 border border-white/10 rounded-full hover:bg-white/10 transition-colors text-sm font-medium text-white">
                      <Copy className="w-4 h-4" /> Copy
                    </button>
                    <button onClick={handleDownload} className="px-4 py-2 flex items-center gap-2 bg-neon-blue/10 border border-neon-blue/30 text-neon-blue rounded-full hover:bg-neon-blue/20 transition-colors text-sm font-bold">
                      <Download className="w-4 h-4" /> Download CSV
                    </button>
                  </>
                )}
                <button 
                  onClick={() => { setResults(null); setFile(null); }} 
                  className="px-6 py-2 ml-4 bg-white text-space-900 rounded-full hover:bg-gray-200 transition-colors font-bold"
                >
                  New Analysis
                </button>
              </div>
            </div>
            
            {results.length === 1 ? (
              // Single Result View
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6 relative z-10">
                <div className="bg-white/5 p-6 rounded-2xl border border-white/5 hover:border-neon-blue/30 transition-colors">
                  <p className="text-neon-blue text-sm mb-2 uppercase tracking-widest font-bold">Age</p>
                  <p className="text-4xl font-black text-white">
                    {results[0].predictions.age.estimate !== null ? results[0].predictions.age.estimate.toFixed(1) : 'N/A'} 
                    {results[0].predictions.age.estimate !== null && <span className="text-lg text-gray-500 font-medium">yrs</span>}
                  </p>
                </div>
                <div className="bg-white/5 p-6 rounded-2xl border border-white/5 hover:border-neon-blue/30 transition-colors">
                  <p className="text-neon-blue text-sm mb-2 uppercase tracking-widest font-bold">Ancestry</p>
                  <p className="text-4xl font-black text-white text-glow text-neon-blue">{results[0].hard_labels.ancestry}</p>
                </div>
                <div className="bg-white/5 p-6 rounded-2xl border border-white/5 hover:border-neon-blue/30 transition-colors">
                  <p className="text-neon-blue text-sm mb-2 uppercase tracking-widest font-bold">Eye Color</p>
                  <p className="text-4xl font-black text-white capitalize">{results[0].hard_labels.eye_color}</p>
                </div>
                <div className="bg-white/5 p-6 rounded-2xl border border-white/5 hover:border-neon-blue/30 transition-colors">
                  <p className="text-neon-blue text-sm mb-2 uppercase tracking-widest font-bold">Hair Color</p>
                  <p className="text-4xl font-black text-white capitalize">{results[0].hard_labels.hair_color}</p>
                </div>
              </div>
            ) : (
              // Batch Table View
              <div className="relative z-10 overflow-x-auto rounded-xl border border-white/10">
                <table className="w-full text-left text-sm text-gray-300">
                  <thead className="text-xs uppercase bg-white/5 text-neon-blue border-b border-white/10">
                    <tr>
                      <th className="px-6 py-4 font-bold tracking-wider">Sample ID</th>
                      <th className="px-6 py-4 font-bold tracking-wider">Age</th>
                      <th className="px-6 py-4 font-bold tracking-wider">Ancestry</th>
                      <th className="px-6 py-4 font-bold tracking-wider">Eye Color</th>
                      <th className="px-6 py-4 font-bold tracking-wider">Hair Color</th>
                      <th className="px-6 py-4 font-bold tracking-wider">Skin Color</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 bg-space-800/50">
                    {results.map((r: PredictionResult, idx: number) => (
                      <tr key={idx} className="hover:bg-white/5 transition-colors">
                        <td className="px-6 py-4 font-medium text-white">{r.sample_id}</td>
                        <td className="px-6 py-4 font-semibold">
                          {r.predictions.age.estimate !== null ? `${r.predictions.age.estimate.toFixed(1)} yrs` : 'N/A'}
                        </td>
                        <td className="px-6 py-4">
                          <span className="px-2.5 py-1.5 rounded-md text-xs font-bold bg-neon-blue/10 text-neon-blue border border-neon-blue/20">
                            {r.hard_labels.ancestry}
                          </span>
                        </td>
                        <td className="px-6 py-4 capitalize font-semibold">{r.hard_labels.eye_color}</td>
                        <td className="px-6 py-4 capitalize font-semibold">{r.hard_labels.hair_color}</td>
                        <td className="px-6 py-4 capitalize font-semibold">{r.hard_labels.skin_color}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            
            {/* Results Legend */}
            <div className="mt-8 p-6 bg-white/5 border border-white/10 rounded-2xl">
              <h4 className="text-sm font-bold text-neon-blue uppercase tracking-wider mb-4 flex items-center gap-2">
                <ShieldAlert className="w-4 h-4" /> Result Interpretation Guide
              </h4>
              <div className="grid md:grid-cols-3 gap-6 text-sm text-gray-400">
                <div>
                  <strong className="text-white">Age (N/A)</strong>
                  <p className="mt-1">Indicates missing Epigenetic DNA Methylation (CpG) data in your CSV. Age cannot be predicted from standard DNA SNPs.</p>
                </div>
                <div>
                  <strong className="text-white">Skin Color (Intermediate)</strong>
                  <p className="mt-1">Biologically represents olive to light-brown skin tones (common in Mediterranean, Hispanic, or South Asian descent).</p>
                </div>
                <div>
                  <strong className="text-white">Ancestry Bias</strong>
                  <p className="mt-1">If your sequence lacks the required 2,500+ global SNPs, the model may default to its statistical baseline (e.g., AFR) due to missing features.</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
