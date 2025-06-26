import subprocess
import requests

ORIGINAL_URL = 'https://osv-grpc-v1-original-784002525137.us-central1.run.app'
NEW_URL = 'https://osv-grpc-v1-new-784002525137.us-central1.run.app'

queries = [
  {'package': {'ecosystem': 'PyPI', 'name': 'tensorflow'}, 'version': '1.3.0'},
  {'package': {'ecosystem': 'Debian:11', 'name': 'wpewebkit'}, 'version': '2.28.0-1'},
  {'package': {'ecosystem': 'Go', 'name': 'stdlib'}, 'version': '1.19.1'},
]

TESTS_PER = 20

def main():
  tok = subprocess.run(['gcloud', 'auth', 'print-identity-token'], capture_output=True, text=True).stdout.strip()

  for i, query in enumerate(queries):
    print(query)
    for _ in range(TESTS_PER):
      resp_orig = requests.post(f'{ORIGINAL_URL}/v1/query', json=query, headers={'Authorization': f'bearer {tok}', 'User-Agent': f'query-test-{i}'}).json()
      resp_new = requests.post(f'{NEW_URL}/v1/query', json=query, headers={'Authorization': f'bearer {tok}', 'User-Agent': f'query-test-{i}'}).json()
      
      # if resp_orig != resp_new:
      #   print(resp_orig)
      #   print(resp_new)


if __name__ == '__main__':
  main()
