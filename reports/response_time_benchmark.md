# /recommend Response Time Benchmark

Generated: 2026-08-19T11:18:52.662477+00:00

Target (paper Table 11): **< 5 seconds per request**

## Sequential requests (normal load, one at a time)

- Requests: 20
- Mean: 0.143s | Median: 0.140s | Min: 0.093s | Max: 0.272s | P95: 0.186s
- Under target: 20/20

## Concurrent requests (light concurrent load)

- Requests: 10 fired simultaneously (10 worker threads)
- Mean: 0.923s | Median: 1.124s | Min: 0.181s | Max: 1.232s | P95: 1.232s
- Under target: 10/10

## Verdict: PASS

Note: this measures the FastAPI service directly on localhost, not through the PHP app's curl call or over a network — real end-user latency (PHP -> curl -> this API -> back to PHP -> page render) will be somewhat higher. Re-run this after deploying to whatever environment will actually be used for TAM/ISO testing if that differs from localhost.

## Raw sequential timings (seconds)

0.272, 0.132, 0.111, 0.093, 0.128, 0.146, 0.143, 0.107, 0.152, 0.162, 0.153, 0.109, 0.131, 0.141, 0.140, 0.105, 0.169, 0.186, 0.167, 0.109

## Raw concurrent timings (seconds)

0.665, 1.232, 1.053, 0.181, 1.231, 1.228, 1.006, 0.223, 1.215, 1.194
