# HW4 N+1 Metrics

| Page size | Version | SQL statements/request | p50 ms | p95 ms | p99 ms |
|---:|---|---:|---:|---:|---:|
| 10 | fixed | 1.0 | 1.311 | 1.445 | 1.453 |
| 10 | naive | 11.0 | 3.732 | 6.424 | 8.354 |
| 50 | fixed | 1.0 | 1.831 | 1.994 | 2.063 |
| 50 | naive | 51.0 | 11.779 | 12.495 | 14.270 |
| 200 | fixed | 1.0 | 3.507 | 12.956 | 14.050 |
| 200 | naive | 201.0 | 42.943 | 45.356 | 47.710 |

## Speed-up

- Page size 10: 2.85x faster by p50 latency
- Page size 50: 6.43x faster by p50 latency
- Page size 200: 12.24x faster by p50 latency