# Related Systems (Section 3.8)

For each system: what it does that this project does not, and what this project does
that it does not.

## Stock xv6-riscv

**What stock xv6 does that this system does not:** ships as buildable source for its
entire kernel (this project's kernel `.c` files are withheld for this milestone by
design, not by the upstream project); stays minimal and single-purpose as a teaching
OS with no networking, no threads, no shared memory, and no resource-limit/capability
model — it is deliberately *not* trying to run a real workload.

**What this system does that stock xv6 does not:** a full network stack (ARP/IP/UDP,
`kernel/net.c`), a from-scratch RPC/XDR layer (RFC 5531/4506), a distributed
application (pipeline-parallel LLM inference) running across multiple instances of
itself, threads and shared memory (`thread_create`, `shmget`/`shmat`), and a real
hardening set — stack canaries with genuine boot entropy, ASLR, POSIX resource
limits, a capability bitmask, and W^X enforcement — none of which stock xv6 has.

## Linux

**What Linux does that this system does not:** true multi-user isolation (full uid
*and* gid semantics, file ownership/mode bits, `chown`/`chmod`), full POSIX.1e
capability *sets* (this system has one effective bitmask covering a single
capability, not the ~40 distinct Linux capabilities), syscall-filtering sandboxes
(`seccomp`/`pledge`-equivalents), cgroups-based resource accounting across many
dimensions (this system has exactly two limited resources, `RLIMIT_AS`/`RLIMIT_CPU`),
loadable kernel modules, SMP scheduling at real scale, and a production TCP stack
(this system's transport is UDP-only — RPC record marking over TCP, RFC 5531 §11, is
explicitly unimplemented, per `user/rpc.c`'s header comment).

**What this system does that Linux does not:** nothing Linux *can't* do in principle
— the comparison that matters here is legibility, not capability. Every layer of this
system, kernel included, is small enough to read end-to-end and reason about
exhaustively (the whole point of building the distributed-inference workload on xv6
rather than on Linux, per the project's stated rationale); a security claim here (the
W^X check, the capability-probe ceiling, the HMAC identity check) can be pinned down
to a specific function and line, which is infeasible to do with the same confidence
against the Linux kernel and glibc.

## `xv6-llm-runtime-arch` (github.com/syedtaha22/xv6-llm-runtime-arch — the base this project builds on)

**What it does that this system does not:** establishes the baseline runtime
architecture and single-node inference path this project extends — the starting
point, not a competing design.

**What this system does that it does not:** everything in the L2/L3 layers this
project adds on top of that base — the hardened network stack (ARP/IP/ICMP/UDP
filtering, rate limiting, bogon/ingress checks), the RPC/discovery/ring layer that
turns a single-node runtime into a pipeline-parallel *distributed* one, the
PSK/HMAC worker authentication, the sized capability probe, and the kernel hardening
set (canaries, entropy, resource limits, capabilities, W^X) — none of which the base
runtime architecture includes; it is a single-node inference engine, not a
distributed, adversarially-tested one.

## Exo (github.com/exo-explore/exo) — closest prior-art pipeline-parallel inference system

**What Exo does that this system does not:** runs on real heterogeneous consumer
hardware (phones, laptops, Raspberry Pis) at real model scale, with a far more
capable scheduler that adapts to heterogeneous device throughput and memory, and a
polished user-facing API — none of which this project attempts; this project targets
a from-scratch teaching kernel at toy model scale (15M/110M-parameter checkpoints) as
a research testbed, not a usable inference product.

**What this system does that Exo does not:** authentication on peer discovery (Exo's
peer join has none), encryption/integrity on the wire (this system's RPC is
plaintext but HMAC-authenticated at registration and its packets get real input
validation), and input validation on incoming tensors at the network/RPC boundary.
This is exactly the gap this project's own documentation identifies as its reason
for choosing this workload: Exo is undefended against the same threat model
(capability lying, identity spoofing, result corruption) that this project's L3
layer explicitly targets and partially closes — including the caveat, established by
this project's own adversarial testing, that result corruption (a node that computes
honestly but reports a tampered value) is *not* currently detected here either, so
the comparison is "closes more of the gap than Exo does," not "fully solved."

## Other pipeline-parallel inference systems (general class: Petals, vLLM's pipeline-parallel mode)

**What they do that this system does not:** operate at production model scale
(tens to hundreds of billions of parameters) with batching, continuous scheduling
across many concurrent requests, and tensor parallelism in addition to pipeline
parallelism (this project's own README states tensor parallelism is out of scope for
v1) — throughput and utilization at that scale is simply not this project's goal.

**What this system does that they do not:** runs the *entire* stack, network driver
through inference kernel, inside a from-scratch, auditable teaching OS with no
underlying Linux/CUDA/production-scheduler dependency — every hop's authentication,
every packet's validation, and every allocation's resource accounting is enforced by
code this project's own team can read in full, which is not true of any
production system built on Linux and a mainstream ML runtime.
