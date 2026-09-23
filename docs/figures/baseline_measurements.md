# Baseline Measurements (Section 3.6)

## Method

Fixed workload throughout, per the handout: model `stories15M.bin` (id 1), steps=32,
temperature=0 (`-t 0`, always). Single-node runs at `XV6_CPUS=1` (`boot.sh` defaults
to 3 cores; every measured single-node run here explicitly passed
`XV6_CPUS=1 ./boot.sh`). Ring runs use `distinf_sim.py`'s default `--smp 8` per node
(unchanged from default so the 2- and 3-worker figures are measured under the same
per-node core budget as each other).

**Primary number: wall-clock duration**, taken directly from each run's own reported
timing — `Inference` (ms) from `llama`'s built-in profiler for single-node, and the
`generation ... in Xs` line from `distinf_sim.py`'s run summary for the ring. Using
`Inference` rather than `Total (E2EL)` for single-node excludes the one-time
network weight-fetch cost (dominated by emulated-UDP transfer time, not the model's
compute cost), matching what the ring's `generation` time also measures (compute +
ring network hops for the shard path, excluding the separate shard *loading* phase
that precedes it).

**Secondary numbers: cycles and instructions retired**, computed rather than
sampled live per run. This needs justification: `rdcycle`/`rdinstret` were tested
directly with gdb against the halted kernel (`docs/transcripts/cycle_instret_probe.txt`,
Observations Log #5) and found to advance in lockstep with real elapsed time *even
while the guest vCPU was provably halted and executed zero instructions* — under
this QEMU configuration (no `-icount`), these CSRs are wall-clock-derived, not true
per-instruction counters, and empirically `instret ≈ cycle` throughout (implied
IPC ≈ 1.00 at all times, including idle). A live per-run gdb sample would therefore
carry no information beyond the wall-clock time already measured. Cycles and
instructions retired are instead reported as `wall_clock_seconds × 2.2597×10⁹`,
using the scale factor established by that same probe (two samples, 5.00s apart,
Δinstret = 11,298,623,360, Δcycle = 11,298,625,329). This is reported per the
handout's own instruction to favour ratios/relative comparisons over absolute
values — the derived figures are internally consistent for that purpose even though
they are not literal hardware-counted values.

## Single-Node (XV6_CPUS=1)

| Prompt | Inference (ms) | Cycles (derived) | Instructions retired (derived) |
|---|---:|---:|---:|
| "Once upon a time" | 8,624 | 1.949 × 10¹⁰ | 1.949 × 10¹⁰ |
| "The quick brown fox" | 11,770 | 2.660 × 10¹⁰ | 2.660 × 10¹⁰ |
| "In the beginning" | 7,266 | 1.642 × 10¹⁰ | 1.642 × 10¹⁰ |
| **Mean** | **9,220** | **2.083 × 10¹⁰** | **2.083 × 10¹⁰** |

Source: `docs/transcripts/baseline_singlenode.txt` (all three prompts run in one
boot session, weights fetched once and cached — see the `Inference` field of each
run's own `SYSTEM PERFORMANCE METRICS` block; `Total (E2EL)` for the first prompt
additionally includes the one-time ~76.6s weight fetch, excluded here as explained
in Method).

Run-to-run variance is real and worth flagging: identical workload (32 steps, same
model, same 1,376 `matmul` calls per run per the function-profiling table), yet
per-run `matmul` self-time ranged 7,085–11,458 ms across the three prompts — a ~40%
swing attributable to host scheduling noise (this machine is a shared, CPU-
oversubscribed WSL2 host throughout this session; see Observations Log #1/#5),
not to the workload itself. The mean is reported precisely because of this variance.

## Multi-Node Ring (first prompt, "Once upon a time")

| Configuration | Generation time (32 tokens) | Cycles (derived) | Instructions retired (derived) | Compute-only (sum of `compute_us`/token × 32) | Network (sum of `network`/token × 32) |
|---|---:|---:|---:|---:|---:|
| 2 workers | 79.2 s | 1.790 × 10¹¹ | 1.790 × 10¹¹ | 14.94 s | 52.44 s |
| 3 workers | 93.3 s | 2.108 × 10¹¹ | 2.108 × 10¹¹ | 12.23 s | 67.96 s |

Source: `docs/transcripts/ring_2workers_transcript.txt`,
`docs/transcripts/baseline_ring_3workers.txt` — each run's own `run summary` block
(`generation`, `latency/token (avg over 32): ring rtt ... = compute ... + network ...`).
Both rings reproduced the single-node token stream exactly ("Once upon a time,
there was a little girl named Lily...").

**The ring is slower in wall-clock terms than the single-node mean, and 3 workers is
slower than 2** — the opposite of what "more parallelism" might suggest, but
expected here: each ring hop pays a full RPC round trip over an emulated network
segment (network time dominates per-token latency in both configurations — 66% at
2 workers, 73% at 3 — and grows with worker count as expected, since more workers
means more hops per token), while compute time per token *drops* as workers
increase (each worker does less of the model: `w1 [0,2) | w2 [2,4) | w3 [4,6)` at 3
workers vs. `w1 [0,3) | w2 [3,6)` at 2), the opposite direction from overall
latency. This is the expected
shape for pipeline parallelism at small model scale over a slow transport: it only
pays off once per-shard compute exceeds the added network cost, which does not
hold for a 15M-parameter model on an emulated UDP segment. The measurement
directly supports the project's own stated v1 scope note (sequential per-token
pipeline, no batching) — throughput, not latency, is where pipeline parallelism
would need to be evaluated for this to look favourable, and that is out of scope
for a single generation run.
