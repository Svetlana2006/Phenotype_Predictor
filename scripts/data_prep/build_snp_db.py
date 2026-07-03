import urllib.request, json, time, sys

rs_targets = ['rs312262906_A', 'rs11547464_A', 'rs885479_T', 'rs1805008_T', 'rs1805005_T', 'rs1805006_A', 'rs1805007_T', 'rs1805009_C', 'rs201326893_A', 'rs2228479_A', 'rs1110400_C', 'rs28777_C', 'rs16891982_C', 'rs12821256_G', 'rs4959270_A', 'rs12203592_T', 'rs1042602_T', 'rs1800407_A', 'rs2402130_G', 'rs12913832_T', 'rs2378249_C', 'rs12896399_T', 'rs1393350_T', 'rs683_G', 'rs3114908_T', 'rs1800414_C', 'rs10756819_G', 'rs2238289_C', 'rs17128291_C', 'rs6497292_C', 'rs1129038_G', 'rs1667394_C', 'rs1126809_A', 'rs1470608_A', 'rs1426654_G', 'rs6119471_C', 'rs1545397_T', 'rs6059655_T', 'rs12441727_A', 'rs3212355_A', 'rs8051733_C']

comp_map = {'A':'T', 'T':'A', 'C':'G', 'G':'C'}

out = open('full_snp_db.txt', 'w')
out.write('SNP_FLANKING_DB = {\n')

def fetch_with_retry(url, headers, max_retries=3):
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                print(f"Rate limited or server error. Retrying in 2 seconds... (Attempt {attempt+1})")
                time.sleep(2)
            else:
                raise e
        except Exception as e:
            print(f"Exception: {e}. Retrying... (Attempt {attempt+1})")
            time.sleep(2)
    raise Exception("Max retries reached")

for item in rs_targets:
    rs_id, target = item.split('_')
    try:
        url = f'https://rest.ensembl.org/variation/human/{rs_id}?content-type=application/json'
        var_data = fetch_with_retry(url, {'Content-Type': 'application/json'})
        data = json.loads(var_data)
            
        mapping = data['mappings'][0]
        chrom = mapping['seq_region_name']
        start = mapping['start']
        end = mapping['end']
        
        # We need the 15bp before start and 15bp after end. (in case it's an indel where start != end)
        seq_url = f'https://rest.ensembl.org/sequence/region/human/{chrom}:{start-15}..{end+15}?content-type=text/plain'
        seq_data = fetch_with_retry(seq_url, {'Content-Type': 'text/plain'})
        full_seq = seq_data.decode('utf-8').strip()
            
        up = full_seq[:15]
        down = full_seq[-15:]
        
        out.write(f'    "{rs_id}": {{"up": "{up}", "down": "{down}", "target_allele": "{target}", "complement": "{comp_map.get(target, "N")}"}},\n')
        out.flush()
        print(f'Success {rs_id}')
        
    except Exception as e:
        print(f'Failed {rs_id}: {e}')
        
    time.sleep(0.5)

out.write('}\n')
out.close()
print("Done writing to full_snp_db.txt")
