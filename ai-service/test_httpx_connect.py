import httpx

url = "http://127.0.0.1:8000/docs"
try:
    response = httpx.get(url, timeout=5)
    print(f"Status: {response.status_code}")
    print(f"Content (first 200 chars):\n{response.text[:200]}")
except Exception as e:
    print(f"Connection error: {e}")
