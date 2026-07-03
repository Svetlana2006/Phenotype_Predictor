import requests

print("Logging in...")
res = requests.post("http://127.0.0.1:8000/api/v1/auth/login", data={"username": "test@phenotype.com", "password": "password123"})
if res.status_code != 200:
    print("Login failed:", res.text)
    exit()

token = res.json()["access_token"]
print("Logged in. Token acquired. Sending prediction...")

files = {'file': open(r"c:\Users\Svetlana\Phenotype_Predictor\data\raw\igsr\hirisplex_genotypes\hirisplex_webtool_input.csv", 'rb')}
headers = {'Authorization': f'Bearer {token}'}

try:
    predict_res = requests.post("http://127.0.0.1:8000/api/v1/predict", files=files, headers=headers, timeout=10)
    print("Status Code:", predict_res.status_code)
    print("Response snippet:", predict_res.text[:500])
except Exception as e:
    print("Request failed:", e)
