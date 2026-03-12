import requests
import json

url = "http://localhost:8000/api/whatsapp/webhook"
headers = {
    "Authorization": "Bearer mock-token",
    "Content-Type": "application/json"
}

payload = {
    "phone_number": "0128528444",
    "message": "i want to order 5 mouse"
}

response = requests.post(url, headers=headers, json=payload)
print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2))
