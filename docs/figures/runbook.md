# Runbook (Section 3.2)

What a new team member needs to reproduce all three configurations from a clean
checkout. Followed literally, in order, on a clean machine.

## Prerequisites

- A Debian/Ubuntu Linux environment. **On Windows, this means WSL2** — native
  Windows cannot run this toolchain. If using WSL2, one extra step is required
  beyond a default install (see the callout below).
- `git`, `python3` with `venv`, and internet access to fetch model checkpoints and
  apt packages.

**WSL2-only prerequisite (skip on native Linux):** the multi-node ring configuration
uses QEMU multicast networking (`-netdev socket,mcast=...`) between the host and
guest VMs. **WSL2's default NAT networking mode does not forward this traffic** —
the ring will hang and fail with `never assigned layers within 900s` /
`arp_lookup: resolution timed out`. Fix, once, before attempting the ring:

```
# In a Windows PowerShell/cmd prompt (not inside WSL):
notepad %USERPROFILE%\.wslconfig
```
Add:
```
[wsl2]
networkingMode=mirrored
```
Then `wsl --shutdown` and reopen a WSL terminal. This is required only for the ring
(`distinf_sim.py`); the single-node and weight-fetch configurations work under
either networking mode. See Observations Log #1 for the full diagnosis.

## 1. Clone and install the toolchain

```bash
git clone <your fork/clone URL>
cd <cloned directory>

sudo apt update
sudo apt install -y git build-essential gdb-multiarch qemu-system-misc \
     gcc-riscv64-linux-gnu binutils-riscv64-unknown-elf python3-venv

python3 -m venv .venv
source .venv/bin/activate
pip install scapy pytest coloredlogs
```

## 2. Fetch the model checkpoints (~495 MB, ~2-3 min)

```bash
chmod +x fetch-models.sh boot.sh boot-gdb.sh
./fetch-models.sh
```
Expected: `./fetch-models.sh --check` reports all three files present with matching
sizes (`stories15M.bin` 60,816,028 B, `tokenizer.bin` 433,869 B, `stories110M.bin`
438,381,596 B).

## 3. Single node

```bash
# terminal 1
source .venv/bin/activate
python server/server.py
# expect three "Loaded file" lines and "Server listening on 0.0.0.0:9999 (UDP)"

# terminal 2
./boot.sh
# at the xv6 "$ " prompt:
llama -n 32 -i "Once upon a time" -t 0
# exit QEMU: Ctrl-A, release, then x
```
Expected: the first run sits at "Fetching from server..." for 1-2 minutes (first
weight fetch over emulated UDP), then prints generated text and a profiling report
ending in a `SYSTEM PERFORMANCE METRICS` block.

## 4. Weight-fetch path

```bash
# with server/server.py still running from step 3:
./boot.sh
# at the xv6 prompt:
testftp
```
Expected: two `PASS` lines — `Successfully fetched tokenizer: 433869 bytes` and
`Successfully fetched weights: 60816028 bytes`, each with a SHA-256 line.

## 5. Multi-node ring

Requires the WSL2 mirrored-networking prerequisite above if applicable. Stop
`server/server.py` first — the ring simulator starts its own weight server on the
same port.

```bash
python server/distinf_sim.py --workers 2 --model 1 --steps 32 \
    --prompt "Once upon a time"
```
Expected: `[sim] OK` lines for boot, registration, layer assignment, and shard
residency, then `[sim] ==== generated ====` with the same text the single-node run
produced, then `[sim] PASS`. Kill any leftover `qemu-system-riscv64` processes
before starting a second run — the nodes share one network segment and two runs
cannot overlap.

**Known flakiness (WSL2 specifically):** even with mirrored networking enabled, the
ring's large UDP transfers occasionally lose a small fraction of chunks and the
run fails with `Transfer failed: received only N/72001 chunks after 6 rounds`. This
recurred intermittently across repeated identical invocations on this host and is
not fixed by retrying the runbook steps differently — see Observations Log #1. A
plain retry of the same command usually succeeds.

## 6. Regression suites

```bash
pytest server/kernel_regression_test.py -v --noconftest       # expect: 14 passed
pytest server/weightfetch_regression_test.py -v --noconftest  # expect: 4 passed
pytest server/distinf_regression_test.py -v --noconftest      # expect: 2 passed, 6 skipped
```
On this host, `distinf_regression_test.py`'s two ring-based tests failed
reproducibly (3/3 attempts) with the same environment-level flakiness as step 5,
despite a manual `distinf_sim.py` invocation succeeding — see Observations Log #1.

## 7. Reverse-engineering the kernel (warm-up + kernel trace)

```bash
cd xv6-riscv
riscv64-unknown-elf-nm kernel/kernel | grep -E ' [tT] '
riscv64-unknown-elf-objdump -d kernel/kernel
cd ..

# kernel debugger, in one combined shell session:
(./boot-gdb.sh < /dev/null > console.txt 2>&1 &)
sleep 4
gdb-multiarch -batch -ex "target remote localhost:26000" \
    -ex "break sys_exec" -ex "continue" -ex "backtrace" \
    -ex "info registers a0 a1 a2" xv6-riscv/kernel/kernel
```
**WSL2 note:** run the `boot-gdb.sh` background-launch and the `gdb-multiarch`
connect in the *same* shell invocation/session. Launching them in separate
terminal sessions that don't share a process group caused the backgrounded QEMU
process to receive `SIGHUP` and die before gdb could connect, on this host.
