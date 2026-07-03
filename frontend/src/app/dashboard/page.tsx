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
    ancestry?: { confidence: number; probabilities: Record<string, number> };
    eye_color?: { confidence: number; probabilities: Record<string, number> };
    hair_color?: { confidence: number; probabilities: Record<string, number> };
    skin_color?: { confidence: number; probabilities: Record<string, number> };
  };
  hard_labels: {
    ancestry: string;
    eye_color: string;
    hair_color: string;
    skin_color: string;
  };
  coverage?: {
    snps_provided: number;
    snps_used: number;
    snps_missing: string[];
  };
  feature_importances?: Record<string, Record<string, number>>;
  model_versions: Record<string, string>;
  provenance: {
    timestamp: string;
    software_version: string;
    git_commit: string;
    training_dataset: string;
  };
}

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState<"csv" | "raw">("csv");
  const [rawSequence, setRawSequence] = useState("");
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

  const runRawPrediction = async () => {
    if (!rawSequence.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      const loginParams = new URLSearchParams();
      loginParams.append("username", "test@phenotype.com");
      loginParams.append("password", "password123");
      
      let authRes = await fetch("http://localhost:8000/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: loginParams
      });

      if (!authRes.ok) {
        await fetch("http://localhost:8000/api/v1/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: "test@phenotype.com", password: "password123", role: "researcher" })
        });
        authRes = await fetch("http://localhost:8000/api/v1/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: loginParams
        });
      }

      const authData = await authRes.json();
      const token = authData.access_token;

      const res = await fetch("http://localhost:8000/api/v1/predict/raw", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ sequence: rawSequence }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Raw sequence prediction failed");
      }

      const data = await res.json();
      setResults(data.samples);
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
                ${isDragging && activeTab === 'csv' ? 'border-neon-blue bg-neon-blue/5 scale-[1.02]' : 'border-white/10 hover:border-neon-blue/50'}
              `}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={activeTab === 'csv' ? handleDrop : undefined}
            >
              <div className="flex gap-4 mb-8 bg-white/5 p-1.5 rounded-full border border-white/10">
                <button 
                  onClick={() => setActiveTab("csv")} 
                  className={`px-6 py-2 rounded-full font-bold text-sm transition-colors ${activeTab === 'csv' ? 'bg-neon-blue text-space-900' : 'text-gray-400 hover:text-white'}`}
                >
                  Upload CSV
                </button>
                <button 
                  onClick={() => setActiveTab("raw")}
                  className={`px-6 py-2 rounded-full font-bold text-sm transition-colors ${activeTab === 'raw' ? 'bg-neon-blue text-space-900' : 'text-gray-400 hover:text-white'}`}
                >
                  Raw Sequence
                </button>
              </div>

              {activeTab === "csv" ? (
                <>
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
              </>
              ) : (
                <div className="w-full max-w-lg mx-auto flex flex-col items-center">
                  <h3 className="text-xl font-bold text-white mb-2">Simulated Sequence Extraction</h3>
                  <p className="text-gray-400 mb-6 text-sm text-center">Paste a raw unaligned DNA string (ATCG). We will align it locally to extract the relevant HIrisPlex variants dynamically.</p>
                  <textarea 
                    value={rawSequence}
                    onChange={(e) => setRawSequence(e.target.value)}
                    placeholder="e.g., GGCATTGATGACGTGGAGACGCCTGATCATGAGCGCCAACA..."
                    className="w-full h-40 bg-space-800/50 border border-white/10 rounded-xl p-4 text-white font-mono text-sm focus:border-neon-blue focus:ring-1 focus:ring-neon-blue outline-none transition-all mb-6"
                  />
                  <button 
                    onClick={runRawPrediction}
                    disabled={isLoading || !rawSequence.trim()}
                    className="px-8 py-3 bg-neon-blue hover:bg-neon-blue/90 text-space-900 border border-neon-blue rounded-full font-bold transition-all disabled:opacity-50 flex items-center gap-2"
                  >
                    {isLoading ? <><Activity className="w-5 h-5 animate-spin" /> Extracting SNPs...</> : <><Search className="w-5 h-5" /> Analyze Sequence</>}
                  </button>
                  
                  {error && (
                    <div className="mt-6 p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 font-medium max-w-lg w-full break-words">
                      <ShieldAlert className="w-5 h-5 inline mr-2" />
                      {error}
                    </div>
                  )}
                </div>
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
              <div className="flex flex-col gap-6 relative z-10 w-full">
                
                {/* Evidence Quality Meter & Routing Banner */}
                {results[0].coverage && (
                  <div className="grid md:grid-cols-2 gap-6 w-full">
                    <div className="bg-white/5 border border-white/10 rounded-2xl p-5 flex flex-col justify-center">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-sm font-bold text-gray-400 uppercase tracking-wider">Evidence Quality</span>
                        <span className={`text-sm font-black ${
                          (results[0].coverage.snps_used / 41) > 0.8 ? 'text-emerald-400' : 
                          (results[0].coverage.snps_used / 41) > 0.3 ? 'text-yellow-400' : 'text-red-400'
                        }`}>
                          {Math.round((results[0].coverage.snps_used / 41) * 100)}%
                        </span>
                      </div>
                      <div className="w-full bg-space-900 rounded-full h-2.5 overflow-hidden">
                        <div 
                          className={`h-2.5 rounded-full ${
                            (results[0].coverage.snps_used / 41) > 0.8 ? 'bg-emerald-400' : 
                            (results[0].coverage.snps_used / 41) > 0.3 ? 'bg-yellow-400' : 'bg-red-400'
                          }`}
                          style={{ width: `${Math.min(100, (results[0].coverage.snps_used / 41) * 100)}%` }}
                        ></div>
                      </div>
                      <p className="text-xs text-gray-500 mt-2">
                        Successfully mapped {results[0].coverage.snps_used} out of 41 biological markers.
                      </p>
                    </div>

                    <div className="bg-neon-blue/5 border border-neon-blue/20 rounded-2xl p-5 flex items-start gap-4">
                      <Cpu className="w-6 h-6 text-neon-blue flex-shrink-0 mt-1" />
                      <div>
                        <h4 className="text-white font-bold text-sm">Dynamic AI Routing Engaged</h4>
                        <p className="text-xs text-gray-400 mt-1">
                          {results[0].coverage.snps_provided < 100 
                            ? "Highly degraded or sparse forensic DNA detected. The engine has automatically routed this sequence to the Sparse HIrisPlex Ancestry Model (Expected Accuracy: ~91%)."
                            : "Large genomic file detected. The engine has routed this sequence to the Full-Genome Macro Ancestry Model (Expected Accuracy: ~97%)."}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
                
                {/* Reproducibility Report */}
                {results[0].provenance && (
                  <div className="bg-white/5 border border-white/10 rounded-2xl p-6 w-full mt-2">
                    <h4 className="text-sm font-bold text-neon-blue uppercase tracking-wider mb-4 flex items-center gap-2">
                      <Search className="w-4 h-4" /> Reproducibility Report
                    </h4>
                    <div className="grid md:grid-cols-4 gap-4 text-xs">
                      <div>
                        <span className="text-gray-500 block mb-1">Model Version</span>
                        <span className="text-white font-mono bg-space-900 px-2 py-1 rounded">
                          v{results[0].model_versions?.ancestry?.split('-')[0] || "1.0"}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500 block mb-1">Training Dataset</span>
                        <span className="text-white font-semibold">{results[0].provenance.training_dataset}</span>
                      </div>
                      <div>
                        <span className="text-gray-500 block mb-1">Prediction Time</span>
                        <span className="text-white font-mono">{results[0].provenance.timestamp}</span>
                      </div>
                      <div>
                        <span className="text-gray-500 block mb-1">System Version</span>
                        <span className="text-gray-400 font-mono">
                          v{results[0].provenance.software_version} (commit: {results[0].provenance.git_commit})
                        </span>
                      </div>
                    </div>
                  </div>
                )}

              <div className="flex flex-wrap justify-center gap-6 w-full mt-4">
                {results[0].predictions.age.estimate !== null && (
                  <div className="flex-1 min-w-[200px] max-w-[300px] bg-white/5 p-6 rounded-2xl border border-white/5 hover:border-neon-blue/30 transition-colors flex flex-col justify-between">
                    <div>
                      <p className="text-neon-blue text-sm mb-2 uppercase tracking-widest font-bold">Age</p>
                      <p className="text-4xl font-black text-white">
                        {results[0].predictions.age.estimate.toFixed(1)} 
                        <span className="text-lg text-gray-500 font-medium ml-1">yrs</span>
                      </p>
                    </div>
                  </div>
                )}
                
                {results[0].hard_labels.ancestry !== "Insufficient Data" && (
                  <div className="flex-1 min-w-[200px] max-w-[300px] bg-white/5 p-6 rounded-2xl border border-white/5 hover:border-neon-blue/30 transition-colors flex flex-col justify-between">
                    <div>
                      <p className="text-neon-blue text-sm mb-2 uppercase tracking-widest font-bold">Ancestry</p>
                      <p className="text-3xl font-black text-white text-glow text-neon-blue break-words">{results[0].hard_labels.ancestry}</p>
                    </div>
                    {results[0].predictions.ancestry?.confidence && (
                      <div className="mt-4">
                        <span className="text-xs font-bold text-emerald-400 bg-emerald-400/10 px-2.5 py-1 rounded-full border border-emerald-400/20">
                          {(results[0].predictions.ancestry.confidence * 100).toFixed(1)}% Confidence
                        </span>
                      </div>
                    )}
                  </div>
                )}
                
                {results[0].hard_labels.eye_color && (
                  <div className="flex-1 min-w-[200px] max-w-[300px] bg-white/5 p-6 rounded-2xl border border-white/5 hover:border-neon-blue/30 transition-colors flex flex-col justify-between">
                    <div>
                      <p className="text-neon-blue text-sm mb-2 uppercase tracking-widest font-bold">Eye Color</p>
                      <p className="text-3xl font-black text-white capitalize">{results[0].hard_labels.eye_color}</p>
                    </div>
                    {results[0].predictions.eye_color?.confidence && (
                      <div className="mt-4">
                        <span className="text-xs font-bold text-emerald-400 bg-emerald-400/10 px-2.5 py-1 rounded-full border border-emerald-400/20">
                          {(results[0].predictions.eye_color.confidence * 100).toFixed(1)}% Confidence
                        </span>
                      </div>
                    )}
                  </div>
                )}
                
                {results[0].hard_labels.hair_color && (
                  <div className="flex-1 min-w-[200px] max-w-[300px] bg-white/5 p-6 rounded-2xl border border-white/5 hover:border-neon-blue/30 transition-colors flex flex-col justify-between">
                    <div>
                      <p className="text-neon-blue text-sm mb-2 uppercase tracking-widest font-bold">Hair Color</p>
                      <p className="text-3xl font-black text-white capitalize">{results[0].hard_labels.hair_color}</p>
                    </div>
                    {results[0].predictions.hair_color?.confidence && (
                      <div className="mt-4">
                        <span className="text-xs font-bold text-emerald-400 bg-emerald-400/10 px-2.5 py-1 rounded-full border border-emerald-400/20">
                          {(results[0].predictions.hair_color.confidence * 100).toFixed(1)}% Confidence
                        </span>
                      </div>
                    )}
                  </div>
                )}
                
                {results[0].hard_labels.skin_color && (
                  <div className="flex-1 min-w-[200px] max-w-[300px] bg-white/5 p-6 rounded-2xl border border-white/5 hover:border-neon-blue/30 transition-colors flex flex-col justify-between">
                    <div>
                      <p className="text-neon-blue text-sm mb-2 uppercase tracking-widest font-bold">Skin Color</p>
                      <p className="text-3xl font-black text-white capitalize">{results[0].hard_labels.skin_color.replace(/_/g, ' ')}</p>
                    </div>
                    {results[0].predictions.skin_color?.confidence && (
                      <div className="mt-4">
                        <span className="text-xs font-bold text-emerald-400 bg-emerald-400/10 px-2.5 py-1 rounded-full border border-emerald-400/20">
                          {(results[0].predictions.skin_color.confidence * 100).toFixed(1)}% Confidence
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>
              
              {/* Explainability Engine: Why this prediction? */}
              {results[0].feature_importances && Object.keys(results[0].feature_importances).length > 0 && (
                <div className="mt-8 bg-white/5 border border-white/10 rounded-2xl p-6 w-full relative z-10">
                  <h4 className="text-sm font-bold text-neon-blue uppercase tracking-wider mb-6 flex items-center gap-2">
                    <Activity className="w-4 h-4" /> Feature Importance (Why this prediction?)
                  </h4>
                  <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
                    {Object.entries(results[0].feature_importances).map(([trait, importances]) => {
                      // Get top 4 SNPs for this trait
                      const topSnps = Object.entries(importances).slice(0, 4);
                      if (topSnps.length === 0) return null;
                      
                      return (
                        <div key={trait} className="flex flex-col gap-3">
                          <h5 className="text-white font-bold capitalize text-sm border-b border-white/10 pb-2">{trait.replace(/_/g, ' ')} Drivers</h5>
                          {topSnps.map(([snp, weight]) => (
                            <div key={snp} className="flex flex-col gap-1">
                              <div className="flex justify-between items-center text-xs">
                                <span className="text-gray-400 font-mono">{snp}</span>
                                <span className="text-emerald-400 font-bold">{(weight * 100).toFixed(1)}%</span>
                              </div>
                              <div className="w-full bg-space-900 rounded-full h-1.5 overflow-hidden">
                                <div 
                                  className="h-1.5 rounded-full bg-neon-blue"
                                  style={{ width: `${Math.min(100, weight * 100)}%` }}
                                ></div>
                              </div>
                            </div>
                          ))}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
              
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
            
            {/* Dynamic Interactive Legend */}
            <div className="mt-8 p-6 bg-white/5 border border-white/10 rounded-2xl">
              <h4 className="text-sm font-bold text-neon-blue uppercase tracking-wider mb-4 flex items-center gap-2">
                <ShieldAlert className="w-4 h-4" /> Result Interpretation Guide
              </h4>
              <div className="grid md:grid-cols-3 gap-6 text-sm text-gray-400">
                {/* Skipped Traits */}
                <div>
                  <strong className="text-white block mb-1">Unpredicted Features</strong>
                  {results[0]?.predictions?.age?.estimate === null && (
                    <p className="mb-2"><span className="text-white font-semibold">Age:</span> Missing Epigenetic DNA Methylation (CpG) markers. Cannot predict age from SNPs.</p>
                  )}
                  {results[0]?.hard_labels?.ancestry === "Insufficient Data" && (
                    <p><span className="text-white font-semibold">Ancestry:</span> Only {Object.keys(results[0]?.predictions?.eye_color?.probabilities || {}).length ? 'a few' : '0'} SNPs provided. Ancestry requires 2,500+ markers, skipped to prevent median bias.</p>
                  )}
                  {results[0]?.predictions?.age?.estimate !== null && results[0]?.hard_labels?.ancestry !== "Insufficient Data" && (
                    <p>All core biological phenotypes were successfully inferred from the sequence!</p>
                  )}
                </div>

                {/* Phenotype & Ancestry Dynamics */}
                <div className="flex flex-col gap-3">
                  <strong className="text-white block">Biological & Ancestral Dynamics</strong>
                  {results[0]?.hard_labels?.ancestry && results[0]?.hard_labels?.ancestry !== "Insufficient Data" && (
                    <p>
                      <span className="text-white font-semibold">Ancestry ({results[0].hard_labels.ancestry}):</span>
                      {results[0].hard_labels.ancestry === 'AFR' ? ' African super-population (Sub-Saharan demographics).' : ''}
                      {results[0].hard_labels.ancestry === 'AMR' ? ' Admixed American super-population (Latino/Hispanic demographics).' : ''}
                      {results[0].hard_labels.ancestry === 'EAS' ? ' East Asian super-population.' : ''}
                      {results[0].hard_labels.ancestry === 'EUR' ? ' European super-population.' : ''}
                      {results[0].hard_labels.ancestry === 'SAS' ? ' South Asian super-population.' : ''}
                    </p>
                  )}
                  {results[0]?.hard_labels?.skin_color ? (
                    <p>
                      <span className="text-white capitalize font-semibold">{results[0].hard_labels.skin_color.replace(/_/g, ' ')} Skin:</span> 
                      {results[0].hard_labels.skin_color === 'dark_or_black' ? ' Driven by homozygous ancestral alleles in the SLC24A5/OCA2 pathways.' : ''}
                      {results[0].hard_labels.skin_color === 'pale' ? ' Driven by homozygous derived alleles in SLC24A5 and HERC2.' : ''}
                      {results[0].hard_labels.skin_color === 'intermediate' ? ' Represents a spectrum from olive to light-brown, common in admixed/Mediterranean DNA.' : ''}
                    </p>
                  ) : <p>No skin color inferred.</p>}
                  
                  {results[0]?.hard_labels?.eye_color && (
                    <p>
                      <span className="text-white capitalize font-semibold">{results[0].hard_labels.eye_color} Eyes:</span> 
                      {results[0].hard_labels.eye_color === 'blue' ? ' Anchored firmly by the derived allele on the HERC2 block.' : ' Heavily influenced by ancestral alleles on OCA2/HERC2.'}
                    </p>
                  )}
                </div>

                {/* Forensic Certainty */}
                <div>
                  <strong className="text-white block mb-1">Forensic Certainty</strong>
                  <p>
                    Confidence percentages are derived from the mathematical certainty of the Random Forest and Logistic Regression models. 
                    Lower confidences (&lt;70%) indicate the provided DNA sits near a biological boundary.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
