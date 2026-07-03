import pytest
from backend.app.services.sequence_extractor import extract_snps_from_sequence
from phenotype_predictor.predictor import PhenotypePredictor
import os

# Create a fixture to load the predictor once for all tests
@pytest.fixture(scope="module")
def predictor():
    # Make sure we're in the right directory or pass the correct path
    outputs_path = os.path.join(os.path.dirname(__file__), '..', 'outputs')
    return PhenotypePredictor.load(outputs_path)

def test_raw_sequence_extraction():
    # A tiny mock sequence containing rs12913832 (T allele for blue eyes)
    seq = "GCTGGCCCTGGGGCTGTGCTCTTCACCCTGATCTTCGTGTCCGTGTACCGCGTGTTCGGTGGTCTTCCTGGGCCGCCTGGGCCACGTCGGCCGCGCGCACGCCTATGATTTTACTCCATCCTTTTATGTTTAAAAGAGTTCATAGATTTTATTGGTGAAAATGTTTCCCTAAAAACTATCATTTAAAGGTGCTGTTTCTCTAAATTGGTTTGTGCAGAAGACAGTTGGCTGCTCACCAGGATGACAGCAGTGACCGGCCTGAGGAGGACAGAGACCTCTCAGATCTCATGGGAGTCAGTGAGGATAA"
    snps = extract_snps_from_sequence(seq)
    
    # We know this sequence should extract at least one SNP
    assert len(snps) > 0
    # Add explicit checks based on known biology if you have them

def test_phenotype_prediction(predictor):
    # A mock dictionary of SNPs (what extract_snps_from_sequence returns)
    # Let's mock a strong European / Blue Eye signal
    mock_snps = {
        "rs12913832": 2, # TT -> Blue eyes (using 0/1/2 dosage format)
        "rs1426654": 0,  # AA -> Light skin
        "rs16891982": 2, # GG -> European hair
    }
    
    result = predictor.predict(mock_snps)
    
    # Check that predictions are generated
    assert result.eye_color is not None
    assert result.skin_color is not None
    
    # Check confidence is populated
    assert "eye_color" in result.confidence
    
    # Check that the Sparse Ancestry model was used (because we only provided 3 SNPs)
    assert result.snps_provided == 3

def test_missing_data_handling(predictor):
    # Test completely empty data
    result = predictor.predict({})
    
    assert result.snps_provided == 0
    
    # The models should gracefully handle empty data by imputing the median/mode
    # and returning a valid prediction dictionary without crashing.
    if result.hard_labels():
        assert "ancestry" in result.hard_labels()
