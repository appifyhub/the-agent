from web_fetcher import WebFetcher


DEFAULT_URL = "https://httpbin.org/get"

def input_or_def(prompt: str, default: str) -> str:
    user_input = input(prompt).strip()
    return user_input if user_input != "" else default

def main():
    print("Running the URL fetcher...")
    url = input_or_def(f"What is the expected URL? [↩ {DEFAULT_URL}] ", DEFAULT_URL)
    fetcher = WebFetcher(url, auto_fetch = True, verbose = True)
    print(f"Fetch result: {fetcher.html}")

if __name__ == "__main__":
    main()
