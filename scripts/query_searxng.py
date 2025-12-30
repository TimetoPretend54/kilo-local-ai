import os, sys, requests

SEARXNG_URL = "http://localhost:18080/search"

def main():
    query = sys.argv[1] if len(sys.argv) > 1 else input("Search query: ")
    params = {"q": query, "format": "json", "language": "en"}

    r = requests.get(SEARXNG_URL, params=params, timeout=5)
    r.raise_for_status()

    results = r.json().get("results", [])[:5]
    for res in results:
        print(f"- {res.get('title')}")
        print(f"  {res.get('url')}\n")

if __name__ == "__main__":
    main()
