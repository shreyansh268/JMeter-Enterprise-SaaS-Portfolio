<img width="838" height="369" alt="image" src="https://github.com/user-attachments/assets/269bbca8-d38b-4f0c-9d20-9ffdace6c6ed" />


# Enterprise SaaS Load Test — JMeter
**Author:** Shreyansh Sharma | QE Expert  
**Target:** JSONPlaceholder (`jsonplaceholder.typicode.com`) — simulated enterprise REST API  
**Concurrency:** 500 threads | **Ramp:** 120s | **Duration:** 300s  
**SLOs:** p99 < 800ms | Error rate < 1%

---

## User Journey Tested

| Step | Method | Endpoint | Simulates |
|------|--------|----------|-----------|
| 01 | GET | `/users` | Dashboard load |
| 02 | POST | `/posts` | Create record |
| 03 | GET | `/posts?userId=X` | Search / filter |
| 04 | GET | `/posts/{id}` | View detail |
| 05 | DELETE | `/posts/{id}` | Delete record |

---

## Project Structure

```
jmeter-portfolio/
├── enterprise_saas_500.jmx          # Main test plan
├── test_data/
│   └── users.csv                    # Parameterised test data (20 rows)
├── tests/perf/scripts/
│   └── assert_slo.py                # SLO gate — p99 + error rate
└── .github/workflows/
    └── perf-gate.yml                # CI pipeline (smoke + full)
```

---

## Running Locally

### GUI mode (design & debug only)
```bash
jmeter -t enterprise_saas_500.jmx
```

### CLI mode — smoke (50 threads)
```bash
jmeter -n \
  -t enterprise_saas_500.jmx \
  -l results/results.jtl \
  -e -o results/html-report \
  -Jthreads=50 -Jrampup=30 -Jduration=120
```

### CLI mode — full load (500 threads)
```bash
jmeter -n \
  -t enterprise_saas_500.jmx \
  -l results/results.jtl \
  -e -o results/html-report \
  -Jthreads=500 -Jrampup=120 -Jduration=300
```

### Assert SLOs after run
```bash
python3 tests/perf/scripts/assert_slo.py \
  --jtl results/results.jtl \
  --p99-slo 800 \
  --error-slo 0.01 \
  --run-label "Local Full Run"
```

---

## CI Pipeline

| Trigger | Threads | Ramp | Duration | Purpose |
|---------|---------|------|----------|---------|
| Every PR | 50 | 30s | 120s | Smoke gate — blocks merge |
| Nightly (01:00 UTC) | 500 | 120s | 300s | Full soak |
| Manual dispatch | configurable | configurable | configurable | Ad-hoc |

---

## JMeter Elements Used

| Element | Purpose |
|---------|---------|
| `ThreadGroup` | 500 virtual users, ramp + duration via `-J` params |
| `HTTP Request Defaults` | Base URL, protocol, timeouts — applied globally |
| `HeaderManager` | Content-Type + Accept headers — Thread Group scope |
| `CookieManager` | Session cookie handling per thread |
| `CacheManager` | Cache simulation — cleared per iteration |
| `CSVDataSet` | Parameterised userId/postTitle/postBody from file |
| `JSONPathExtractor` | Correlates userId, postId across steps |
| `GaussianRandomTimer` | Realistic think-time (1–4s) between steps |
| `ResponseAssertion` | Status code + body content validation |
| `DurationAssertion` | Per-request 800ms SLO gate |
| `AggregateReport` | p50/p90/p95/p99 per sampler |
| `SummaryReport` | Throughput + error rate |
| `ResponseTimeGraph` | Latency over time visual |


Key Principles

Journey testing, not endpoint testing — all 5 steps run sequentially per thread, simulating a real user session
Correlation over hardcoding — dynamic IDs extracted from responses and injected into subsequent requests
Variance-first — run 5× and report mean p99 ± std before trusting any result
CLI-only for load runs — GUI mode adds JMeter overhead as measurement noise
Duration Assertion ≠ p99 gate — per-request duration assertions flag individual slow requests; assert_slo.py gates on aggregate p99 across the full run
