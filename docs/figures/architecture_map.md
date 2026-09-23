# Architecture Map — Eight Subsystems

Method: rows 2–7 are read directly from `user/*.c` source (file:line below). Rows 1 and 8
live in the kernel, whose `.c` source is withheld, so they are mapped from the binary —
`riscv64-unknown-elf-nm kernel/kernel` for addresses and
`riscv64-unknown-elf-objdump -d --disassemble=<fn> kernel/kernel` for behaviour.

## 1. Network Stack (kernel, from binary)

- **Entry point:** `net_rx`, address `0x800099c6` (`kernel.sym`)
- **Responsibility:** dispatches every received Ethernet II frame by EtherType.
- **From the disassembly:** reads bytes 12–13 of the frame (the EtherType field) as a
  16-bit value. `0x0806` (ARP) branches to `arp_rx` (`0x800094e8`); `0x0800` (IPv4)
  branches to `ip_rx` (`0x80008d9a`); anything else is dropped via `kfree`.
- **Standard:** Ethernet II framing; the two dispatch targets implement RFC 826 (ARP)
  and RFC 791 (IPv4), per the header comments in `kernel/net.h`.

## 2. Remote Procedure Call

- **Entry point:** `rpc_call`, `user/rpc.c:487`
- **Responsibility:** ONC RPC transport over UDP — request/reply framing, retry.
- **Standard:** RFC 5531 (ONC RPC), quoted directly in the file header comment
  (`user/rpc.c:1-6`): "ONC RPC transport layer, RFC 5531 compliant... Record marking
  (RFC 5531 §11) is TCP-only; not implemented here" (this stack is UDP-only).

## 3. Data Serialisation

- **Entry point:** `xdrmem_create`, `user/xdr.c:143`
- **Responsibility:** in-memory XDR encode/decode stream backing every RPC message.
- **Standard:** RFC 4506 (External Data Representation), referenced in `user/rpc.c`'s
  header comment ("XDR encoding per RFC 4506").

## 4. Discovery and Registration

- **Entry point:** `discovery_register`, `user/discovery.c:288`
- **Responsibility:** worker→master registration handshake; proves PSK possession via
  HMAC before a worker is admitted to the ring.
- **Standard:** RFC 2104 / FIPS 198-1 (HMAC), quoted directly at `user/discovery.c:8`:
  "hmac_sha256 — RFC 2104 / FIPS 198-1 keyed MAC over user/sha256.c."

## 5. Ring Driver and Shard Logic

- **Entry points:** `run_master`, `user/distinf.c:1268`; `run_worker`,
  `user/distinf.c:1392`; `shard_load`, `user/shard.c:103`; `shard_forward`,
  `user/shard.c:190`.
- **Responsibility:** `distinf.c` drives registration, layer assignment, and the
  token-by-token ring traversal; `shard.c` computes each worker's layer range within a
  checkpoint and loads only that slice.

## 6. Transformer Kernels

- **Entry point:** `forward`, `user/llama_core.c:742`
- **Responsibility:** the transformer forward pass (attention, matmul, rmsnorm) shared
  by both the single-node driver (`llama.c`) and each ring shard.

## 7. Weight Fetch Client

- **Entry point:** `llm_fetch_file`, `user/ftpclient.c:691`
- **Responsibility:** fetches a checkpoint/tokenizer file over the custom UDP
  file-transfer protocol (LLM-RFTP) from `server/server.py`, chunk by chunk, verifying
  the transfer against a SHA-256 the server reports at connect time.

## 8. Kernel Hardening Set (kernel, from binary)

| Feature | Entry point | Address | What the disassembly shows |
|---|---|---|---|
| Stack canary init | `stackguard_init` | `0x80001e64` | Calls `rand64` (`0x80001f3c`), stores the result to `__stack_chk_guard` (`0x8000cbb0`) — a real per-boot random canary, not a constant. |
| Canary check | `__stack_chk_fail` | `0x80001e80` | Called from guarded functions (e.g. `sys_exec` at `0x80005958`) when the saved canary no longer matches. |
| Entropy pool init | `random_init` | `0x80002000` | Seeds the pool by calling `random_add` 8 times, each time mixing in `rdtime` (the RISC-V cycle/time CSR) plus stack contents — a real boot-time entropy source, not a fixed seed. |
| User-facing entropy syscall | `sys_getentropy` | `0x80001b46` | Standard syscall preamble (`argaddr`/`argint` argument marshalling) around the kernel's entropy pool — the user-side half of the canary/key-randomisation story the README describes. |
| Memory quota (`RLIMIT_AS`) | `rlimit_as_ok` | `0x8000693a` | Compares a process struct field at offset `+72` (current usage) against the requested size, and a field at `+656` (the limit) — returns 1 only if the request stays under the hard limit. |
| Capabilities | `capable` | `0x800069d6` | Loads the calling process's capability bitmask (proc struct offset `+696`), shifts right by the requested bit index, masks bit 0 — single-bitmask capability check, matching the README's "a single effective bitmask suffices for the one capability in use." |
| W^X enforcement | `kexec` | `0x8000489e` | At `0x80004a96`: masks a segment's permission bits (`flags2perm` result) with `0xc` (`PTE_W \| PTE_X` from `kernel/riscv.h:410-411`) and compares to `0xc` — a segment requesting both writable and executable is rejected before it is ever mapped. |

Resource-limit syscalls (`sys_setrlimit`/`sys_getrlimit`, `0x80001982`/`0x80001a44`) and
`sys_exec` (`0x80005838`, which calls into `kexec` for the actual ELF load and W^X
check) round out the set; all addresses above are directly from
`riscv64-unknown-elf-nm kernel/kernel`.
