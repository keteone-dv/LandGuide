import requests
import json

url = "https://naprweb.reestri.gov.ge/api/search"
payload = json.dumps({
    "address": "", "cadcode": "05.30.38.031", "datefrom": None,
    "dateto": None, "page": 1, "person": "", "regno": "", "search": "",
})
headers = {'Content-Type': 'application/json'}
response = requests.request("POST", url, headers=headers, data=payload)

with open("data/samples/napr_sample_response.json", "w", encoding="utf-8") as f:
    f.write(response.text)

print("Saved to data/samples/napr_sample_response.json")
print(response.text)