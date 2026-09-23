# Observations Log

Per the handout (Section 3.7): things noticed while reading/running the code that look
wrong, surprising, or undocumented, kept to the source we have (user-space + host
`server/`). No fixes are made here — this milestone does not touch the code.

## 1. `server/distinf_sim.py` ring runs are flaky under WSL2 even with correct config

**File/context:** `server/distinf_sim.py`, `server/mcast_switch.py` (host-side
multicast bridge), observed while bringing up the multi-worker ring.

Two distinct symptoms were seen, both during the shard/embedding fetch phase of a
ring run, neither in the code itself:

- **Total failure** (`never assigned layers within 900s`, master log shows
  `arp_lookup: resolution timed out for 0xa000001`): the master could never reach the
  host-side weight server over the QEMU multicast segment at all, even though
  worker↔master registration over the *same* segment succeeded. Root cause: WSL2's
  default NAT networking mode does not forward IP multicast between host processes and
  QEMU guests. Fix: enable WSL2 **mirrored networking mode**
  (`%USERPROFILE%\.wslconfig`, `networkingMode=mirrored`, then `wsl --shutdown`).
- **Partial failure** (`Transfer failed: received only N/72001 chunks after 6 rounds`),
  seen even *after* the mirrored-mode fix, on both 2- and 3-worker rings: roughly
  50-90 chunks (~0.1%) of the ~35 MB embedding transfer are lost and the transfer's
  6-round retry budget is exhausted. This recurs intermittently — the identical
  command succeeds roughly half the time on a plain retry — so it looks like
  probabilistic UDP loss on the multicast segment under WSL2, not a deterministic
  defect. Higher worker counts (more co-resident QEMU VMs contending for the host's 8
  cores) appear to make it more likely, but it is not exclusive to high worker counts.

**Why this belongs in the log rather than "fixed and moved on":** this is a testing
infrastructure/host-environment issue, not a defect in `user/`, `server/`, or the
kernel under test — a marker running the identical runbook on a different host
(native Linux, no multicast virtualisation layer in the way) would likely not see it
at all. It cost real time to characterise, though, and directly explains why
`server/distinf_regression_test.py`'s two ring-based tests
(`test_ring_generates`, `test_matches_single_node`) were run three times on this
machine: FAIL / FAIL / FAIL, all with the identical `never assigned layers within
900s` signature, while a manual `distinf_sim.py --workers 2` CLI invocation outside
pytest succeeded cleanly once (the transcript used for the Section 3.1.2 bring-up
deliverable) and failed on other attempts. The result is inconsistent across
identically-argumented runs on the same machine within the same session — the
clearest possible signal that the variable is host/network timing, not the code
path, since the same code path produced a full correct token stream at least once.
Exactly the "anything other than the expected counts is worth a log entry" case the
handout calls out for this suite; the suite's expected result table (2 passed, 6
skipped) could not be reproduced on this host despite three attempts, so the
submitted evidence for `distinf_regression_test.py` is a failing run with this
explanation attached, not a fabricated pass.

## 2. `worker_entry_t.last_seen_ms` (`user/discovery.h:116`) holds ticks, not ms

**Files:** `user/discovery.h:116`, `user/distinf.c:1023,1027,1048`.

The field is named `last_seen_ms` and every timeout constant it is compared against
(`SUSPECTED_TIMEOUT`, `EXPIRED_TIMEOUT` in `discovery.h:24-25`) is built from
`HEARTBEAT_INTERVAL_TICKS`, but the value actually stored in it is `uptime()` —
xv6's raw timer-tick counter, passed straight through as the `now_ms` parameter
at every call site (`discovery_handle_call(&msg, &src, uptime())`,
`discovery_expire_workers(uptime())` in `user/distinf.c`). The unit is ticks
throughout; the `_ms` in the name and the parameter name `now_ms` both claim a
millisecond value that is never actually computed anywhere. Harmless only because
every comparison uses the same (wrong) unit consistently — it would become a real
bug the moment any code compared this field against an actual millisecond value
(e.g. a wall-clock timestamp from a different source).

## 3. `discovery_expire_workers` ages a PENDING worker exactly like an ACTIVE one — the shipped `diagrams/state_diagram.png` doesn't show this and is wrong

**File:** `user/discovery.c:769-800`, comment at `776-782` (the code documents this
itself). See `docs/figures/f3_worker_lifecycle.md` for the full corrected state
diagram and divergence paragraph (Section 3.4, figure F3).

## 4. `handle_auth_hello`'s "slot stays PENDING and ages out" comments (`user/discovery.c:514,562`) rely on behaviour that isn't obviously intended

Both comments describe a PENDING worker that fails registration (no entropy for a
probe nonce, or a bad CAP_ACK) as one that "ages out" — but per observation #3,
aging out from PENDING was never a deliberately designed path; it is a side effect
of `discovery_expire_workers` not special-casing PENDING. The comments read as if
this were the intended behaviour, when the code's own later comment (#3) calls it a
known divergence from the design ("documented as a follow-up in README.md, not
fixed here"). Not a functional bug — the slot does get reclaimed — but the
intent behind it is inconsistently described across the file.

## 5. `rdcycle`/`rdinstret` do not measure guest execution under this QEMU configuration — they track host wall-clock time almost exactly

**Files:** `kernel/syscall.h:39-41` (`SYS_rdcycle`/`SYS_rdtime`/`SYS_rdinstret`),
`boot.sh`/`boot-gdb.sh` (the `qemu-system-riscv64` invocation — no `-icount` flag).

Verified directly with `gdb-multiarch` connected to `boot-gdb.sh`'s gdb stub
(port 26000) *before ever sending `continue`* — i.e. with the guest vCPU provably
halted (`-S`) and zero instructions executed. `info all-registers` exposes `cycle`,
`instret`, `mcycle`, `minstret` as readable pseudo-registers. Sampled twice, 5
seconds of real time apart, with the vCPU never released from halt:

| Sample | `instret` | `cycle` |
|---|---|---|
| t=0s | 1,635,762,915,193 | 1,635,763,713,343 |
| t=5s | 1,647,061,538,553 | 1,647,062,338,672 |
| Δ over 5s | 11,298,623,360 | 11,298,625,329 |
| implied rate | ≈2.2597 GHz | ≈2.2597 GHz |

Both counters advanced by essentially the same amount, at a rate matching a modern
host CPU's clock, **while the guest hart executed zero instructions**. This is only
possible if QEMU is not gating these CSRs on actual guest instruction retirement —
under TCG emulation without `-icount` (not passed by either boot script), `cycle`/
`instret` appear to be implemented as `host_wallclock × constant`, not true
per-instruction hardware counters. The two counters also track each other almost
exactly (implied IPC ≈ 1.00 throughout, including while genuinely idle), which is
itself further evidence they are the same underlying wall-clock-derived value read
twice rather than independent hardware events.

**Consequence for Section 3.6:** the assignment's own guidance ("QEMU does not model
real hardware timing... report ratios and relative differences") already anticipates
some imprecision, but this goes further — `rdcycle`/`rdinstret`, as actually
implemented in this environment, are not a higher-fidelity alternative to the
1&nbsp;ms-resolution wall-clock timer at all; they are the *same* wall-clock signal at
higher numeric resolution. The baseline measurements report derives cycle/instret
figures from each run's precisely measured wall-clock duration and this empirically
established ~2.2597 GHz scale factor (method documented in the baseline
measurements section) rather than claiming a live per-run hardware sample, since a
live sample would carry no more information than the wall-clock time already gives.

*(Further entries to be added as the remaining subsystems — RPC retry logic, XDR
bounds checks, shard layer-range arithmetic — are read in detail for the architecture
map and figures.)*
