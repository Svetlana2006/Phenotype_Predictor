import urllib.request, json, time, sys

rs_targets = ['rs312262906_A', 'rs11547464_A', 'rs885479_T', 'rs1805008_T', 'rs1805005_T', 'rs1805006_A', 'rs1805007_T', 'rs1805009_C', 'rs201326893_A', 'rs2228479_A', 'rs1110400_C', 'rs28777_C', 'rs16891982_C', 'rs12821256_G', 'rs4959270_A', 'rs12203592_T', 'rs1042602_T', 'rs1800407_A', 'rs2402130_G', 'rs12913832_T', 'rs2378249_C', 'rs12896399_T', 'rs1393350_T', 'rs683_G', 'rs3114908_T', 'rs1800414_C', 'rs10756819_G', 'rs2238289_C', 'rs17128291_C', 'rs6497292_C', 'rs1129038_G', 'rs1667394_C', 'rs1126809_A', 'rs1470608_A', 'rs1426654_G', 'rs6119471_C', 'rs1545397_T', 'rs6059655_T', 'rs12441727_A', 'rs3212355_A', 'rs8051733_C']

comp_map = {'A':'T', 'T':'A', 'C':'G', 'G':'C'}

out = open('full_snp_db.txt', 'w')
out.write('SNP_FLANKING_DB = {\n')

for item in rs_targets:
    rs_id, target = item.split('_')
    try:
        url = f'https://rest.ensembl.org/variation/human/{rs_id}?content-type=application/json'
        req = urllib.request.Request(url, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read())
            
        mapping = data['mappings'][0]
        chrom = mapping['seq_region_name']
        start = mapping['start']
        
        seq_url = f'https://rest.ensembl.org/sequence/region/human/{chrom}:{start-15}..{start+15}?content-type=text/plain'
        seq_req = urllib.request.Request(seq_url, headers={'Content-Type': 'text/plain'})
        with urllib.request.urlopen(seq_req, timeout=5) as response2:
            full_seq = response2.read().decode('utf-8').strip()
            
        if len(full_seq) == 31:
            up = full_seq[:15]
            down = full_seq[16:]
            out.write(f'    "{rs_id}": {{"up": "{up}", "down": "{down}", "target_allele": "{target}", "complement": "{comp_map[target]}"}},\n')
            out.flush()
            print(f'Success {rs_id}')
        else:
            print(f'Failed {rs_id}: wrong length {len(full_seq)}')
        
    except Exception as e:
        print(f'Failed {rs_id}: {e}')
        
    time.sleep(0.2)

out.write('}\n')
out.close()
print("Done writing to full_snp_db.txt")
