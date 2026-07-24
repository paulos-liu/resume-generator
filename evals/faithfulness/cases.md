# Faithfulness

The reviewer must classify each rephrasing against its cited source. Near-misses
are the point: a reviewer that passes everything here is broken.

**Expected outcome key:** `supported` | `unsupported`

```json
[
  {"source": "nw.b1", "text": "Reduced p99 checkout latency 73%", "expect": "supported"},
  {"source": "nw.b1", "text": "Reduced checkout latency on a 2M req/day service", "expect": "supported"},
  {"source": "nw.b1", "text": "Led a team of 4 rebuilding checkout", "expect": "supported"},
  {"source": "nw.b1", "text": "Led engineering teams rebuilding checkout", "expect": "unsupported"},
  {"source": "nw.b1", "text": "Cut latency by an order of magnitude", "expect": "unsupported"},
  {"source": "nw.b1", "text": "Owned the checkout product roadmap", "expect": "unsupported"},
  {"source": "nw.b2", "text": "Migrated 38 services to ECS with zero downtime", "expect": "supported"},
  {"source": "nw.b2", "text": "Migrated the entire fleet to containers", "expect": "unsupported"},
  {"source": "nw.b3", "text": "Cut median PR-to-deploy from 4 days to 6 hours", "expect": "supported"},
  {"source": "nw.b3", "text": "Transformed engineering culture org-wide", "expect": "unsupported"},
  {"source": "ndj.b1", "text": "Built a Rust NDJSON parser at 1.8 GB/s single-core", "expect": "supported"},
  {"source": "ndj.b1", "text": "Built high-performance Rust infrastructure used in production at scale", "expect": "unsupported"}
]
```

Note the shape of the unsupported ones: every single one is *more impressive and
less specific* than its source. That is what a stretch looks like in practice.
