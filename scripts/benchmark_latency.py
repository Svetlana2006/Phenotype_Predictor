import time
import psutil
import os
import tracemalloc
from phenotype_predictor.predictor import PhenotypePredictor
from backend.app.services.sequence_extractor import extract_snps_from_sequence

def run_benchmark():
    print("Loading Predictor...")
    outputs_path = os.path.join(os.path.dirname(__file__), '..', 'outputs')
    predictor = PhenotypePredictor.load(outputs_path)
    
    seq = "GCTGGCCCTGGGGCTGTGCTCTTCACCCTGATCTTCGTGTCCGTGTACCGCGTGTTCGGTGGTCTTCCTGGGCCGCCTGGGCCACGTCGGCCGCGCGCACGCCTATGATTTTACTCCATCCTTTTATGTTTAAAAGAGTTCATAGATTTTATTGGTGAAAATGTTTCCCTAAAAACTATCATTTAAAGGTGCTGTTTCTCTAAATTGGTTTGTGCAGAAGACAGTTGGCTGCTCACCAGGATGACAGCAGTGACCGGCCTGAGGAGGACAGAGACCTCTCAGATCTCATGGGAGTCAGTGAGGATAA"
    
    # Warmup
    _ = extract_snps_from_sequence(seq)
    _ = predictor.predict({"rs12913832": 2})

    num_iterations = 100
    
    # Preprocessing Benchmark
    start_time = time.perf_counter()
    for _ in range(num_iterations):
        extract_snps_from_sequence(seq)
    prep_time = (time.perf_counter() - start_time) / num_iterations * 1000 # ms
    
    snps = extract_snps_from_sequence(seq)
    
    # Memory Tracking
    tracemalloc.start()
    
    # Prediction Benchmark
    start_time = time.perf_counter()
    for _ in range(num_iterations):
        predictor.predict(snps)
    pred_time = (time.perf_counter() - start_time) / num_iterations * 1000 # ms
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    peak_mb = peak / 10**6
    
    print(f"Average Preprocessing Time: {prep_time:.2f} ms")
    print(f"Average Prediction Latency: {pred_time:.2f} ms")
    print(f"Total End-to-End Latency: {prep_time + pred_time:.2f} ms")
    print(f"Peak Memory Usage during Inference: {peak_mb:.2f} MB")

if __name__ == "__main__":
    run_benchmark()
