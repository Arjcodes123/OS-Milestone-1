# Difference From Upstream xv6 (Section 3.5)

## 1. Added System Calls

Stock xv6-riscv defines syscalls 1-21 (`SYS_fork` … `SYS_close`, `kernel/syscall.h:2-22`).
This build goes to 59, so **38 syscalls (numbers 22-59) were added**, matching the
handout's estimate exactly. Numbers 22-28 (`trace`, `interpose`, `sigalarm`,
`sigreturn`, `symlink`, `mmap`, `munmap`) have **no corresponding stub in
`user/user.h`** — they are reserved numbers inherited from the upstream MIT 6.828
xv6-labs skeleton this project descends from, but this project never wired a
userland entry point to them, so they are listed for completeness but are not
callable and not part of this project's own work.

| # | Name | Description |
|---|---|---|
| 22 | `trace` | *(no user-space stub; unused xv6-labs leftover)* |
| 23 | `interpose` | *(no user-space stub; unused xv6-labs leftover)* |
| 24 | `sigalarm` | *(no user-space stub; unused xv6-labs leftover)* |
| 25 | `sigreturn` | *(no user-space stub; unused xv6-labs leftover)* |
| 26 | `symlink` | *(no user-space stub; unused xv6-labs leftover)* |
| 27 | `mmap` | *(no user-space stub; unused xv6-labs leftover)* |
| 28 | `munmap` | *(no user-space stub; unused xv6-labs leftover)* |
| 29 | `bind` | Bind the calling process to a UDP port for raw send/recv. |
| 30 | `unbind` | Release a previously bound UDP port. |
| 31 | `send` | Send a UDP datagram (port, dest IP, dest port, buffer, length). |
| 32 | `recv` | Receive a UDP datagram on a bound port (blocking). |
| 33 | `pgpte` | Return the PTE for a given virtual address (page-table introspection). |
| 34 | `kpgtbl` | Print the kernel page table (debug/introspection). |
| 35 | `shmget` | Create/look up a named shared-memory segment (`IPC_CREAT`/`IPC_EXCL`). |
| 36 | `shmat` | Attach a shared-memory segment into the caller's address space. |
| 37 | `shmdt` | Detach a shared-memory segment. |
| 38 | `shmctl` | Control a shared-memory segment (e.g. `IPC_RMID`). |
| 39 | `rdcycle` | Read the RISC-V `cycle` CSR (baseline measurement primitive). |
| 40 | `rdtime` | Read the RISC-V `time` CSR. |
| 41 | `rdinstret` | Read the RISC-V `instret` CSR (instructions retired). |
| 42 | `getramused` | Report the caller's current RAM usage in bytes. |
| 43 | `setrlimit` | Set a POSIX resource limit (`RLIMIT_AS`/`RLIMIT_CPU`) for the caller. |
| 44 | `getrlimit` | Read a POSIX resource limit for the caller. |
| 45 | `capget` | Return the caller's capability bitmask. |
| 46 | `capdrop` | Permanently clear one capability bit for the caller (one-way). |
| 47 | `getentropy` | Fill a buffer with real boot-time entropy (canaries, ASLR, keys). |
| 48 | `getuid` | Return the caller's real uid. |
| 49 | `geteuid` | Return the caller's effective uid. |
| 50 | `setuid` | Set the caller's real (and effective) uid. |
| 51 | `seteuid` | Set the caller's effective uid only. |
| 52 | `recvtimeo` | Receive a UDP datagram with a timeout (bounded blocking `recv`). |
| 53 | `ip` | Return the caller node's own IPv4 address. |
| 54 | `thread_create` | Spawn a new thread sharing the caller's address space. |
| 55 | `thread_join` | Block until the given thread exits. |
| 56 | `thread_exit` | Terminate the calling thread. |
| 57 | `yield` | Voluntarily give up the CPU (used by the matmul/attention thread pool's spin-wait). |
| 58 | `setpriority` | Set a process's scheduling priority. |
| 59 | `udp_bulk` | Declare a bulk UDP flow (port + peer IP) exempt from the per-source rate limiter; privileged (`CAP_NET_ADMIN`). |

A note from the kernel header itself (`kernel/syscall.h:66-74`, quoted verbatim):
the thread syscalls (54-57) were originally numbered 43-47, directly colliding with
the `setrlimit`/`getrlimit`/`capget`/`capdrop`/`getentropy` block above. Because
`syscalls[]` is a designated-initializer array, the collision was not a compile
error — the later initializer silently won, so all five of those POSIX syscalls
dispatched to thread/scheduler handlers instead of their intended implementations
until the thread block was renumbered to 54-57. Already fixed in this build (the
numbering above is current), but worth noting as a real historical defect class
(silent designated-initializer collision) the maintainers document rather than hide.

## 2. File Classification

Grouping the added `user/*.c` files (and the kernel hardening set, mapped from the
binary in Section 3.3) by what they are for:

| Category | Files |
|---|---|
| **Networking** | `kernel/net.c`*, `user/nettest.c`, `user/netecho.c`, `user/rpc.c`/`rpc.h`, `user/xdr.c`/`xdr.h` |
| **Distributed inference** | `user/discovery.c`/`discovery.h`, `user/distinf.c`/`distinf.h`, `user/shard.c`/`shard.h`, `user/dorphan.c`, `user/forphan.c` |
| **Model computation** | `user/llama_core.c`/`llama_core.h`, `user/llama.c`, `user/ftpclient.c`/`ftpclient.h`, `user/shardspike.c` |
| **Hardening** | `kernel/stackguard.c`*, `kernel/random.c`*, `kernel/rlimit.h`, `kernel/capability.h`, `user/canarytest.c`, `user/aslrtest.c`, `user/rlimittest.c`, `user/idtest.c`, `user/wxtest.c`/`wxbad.c`, `user/stackguard.c`, `user/randtest.c` |
| **Measurement** | `user/perf.c`/`perf.h`, `user/testperf.c`, `user/testram.c`, `user/testshm.c` |
| **Test/regression infra (cross-cutting)** | `user/testutil.c`/`testutil.h`, `user/runtests.c`, `user/usertests.c`, `user/rpc_test.c`, `user/xdr_test.c`, `user/testftp.c`, `user/testsha.c`, `user/mutex.c`, `user/sha256.c`/`sha256.h`, `user/xmath.c`/`xstdlib.c`/`xstrlib.c` (freestanding math/libc replacements, needed because the kernel/user split here has no libc) |

\* kernel-side file; `.c` source withheld, classified from its role as established in
Section 3.3 (binary-mapped rows) rather than by reading it directly.
