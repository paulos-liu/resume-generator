# Faithfulness

The reviewer must classify each rephrasing against its cited source. Near-misses
are the point: a reviewer that passes everything here is broken.

**Expected outcome key:** `supported` | `unsupported`

```json
[
  {"id": "case-01-latency-percent", "source": "nw.b1", "text": "Reduced p99 checkout latency 73%", "expect": "supported"},
  {"id": "case-02-latency-scale", "source": "nw.b1", "text": "Reduced checkout latency on a 2M req/day service", "expect": "supported"},
  {"id": "case-03-team-of-4", "source": "nw.b1", "text": "Led a team of 4 rebuilding checkout", "expect": "supported"},
  {"id": "case-04-engineering-teams", "source": "nw.b1", "text": "Led engineering teams rebuilding checkout", "expect": "unsupported"},
  {"id": "case-05-order-of-magnitude", "source": "nw.b1", "text": "Cut latency by an order of magnitude", "expect": "unsupported"},
  {"id": "case-06-checkout-roadmap", "source": "nw.b1", "text": "Owned the checkout product roadmap", "expect": "unsupported"},
  {"id": "case-07-ecs-migration", "source": "nw.b2", "text": "Migrated 38 services to ECS with zero downtime", "expect": "supported"},
  {"id": "case-08-entire-fleet", "source": "nw.b2", "text": "Migrated the entire fleet to containers", "expect": "unsupported"},
  {"id": "case-09-pr-to-deploy", "source": "nw.b3", "text": "Cut median PR-to-deploy from 4 days to 6 hours", "expect": "supported"},
  {"id": "case-10-culture-org-wide", "source": "nw.b3", "text": "Transformed engineering culture org-wide", "expect": "unsupported"},
  {"id": "case-11-ndjson-parser", "source": "ndj.b1", "text": "Built a Rust NDJSON parser at 1.8 GB/s single-core", "expect": "supported"},
  {"id": "case-12-production-at-scale", "source": "ndj.b1", "text": "Built high-performance Rust infrastructure used in production at scale", "expect": "unsupported"}
]
```

Note the shape of the unsupported ones: every single one is *more impressive and
less specific* than its source. That is what a stretch looks like in practice.
