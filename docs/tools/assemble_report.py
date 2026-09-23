#!/usr/bin/env python3
"""Assemble docs/figures/*.md into one report.md ready for pandoc -> LaTeX -> PDF."""
import re
import os

FIG = "docs/figures"
OUT = "docs/report.md"

def read(name):
    with open(os.path.join(FIG, name), encoding="utf-8") as f:
        return f.read()

def insert_image_after_nth_mermaid(text, images):
    """images: list of (index, path, caption) -- 0-based index of the mermaid block."""
    blocks = list(re.finditer(r"```mermaid.*?```", text, re.DOTALL))
    out = []
    last = 0
    img_by_idx = {i: (p, c) for i, p, c in images}
    for i, m in enumerate(blocks):
        out.append(text[last:m.end()])
        if i in img_by_idx:
            path, cap = img_by_idx[i]
            out.append(f"\n\n![{cap}]({path})\n")
        last = m.end()
    out.append(text[last:])
    return "".join(out)

def img(path, cap=""):
    return f"\n\n![{cap}]({path})\n"

def pagebreak():
    return "\n\n\\newpage\n\n"

parts = []

# ---------------------------------------------------------------- title page
parts.append(r"""---
title: "Distributed Inference on xv6 --- Milestone 1: Understand and Characterise"
author: "Team samosaOS"
date: \today
---

\newpage

# Team Information

**Team name:** samosaOS

**Repository:** `https://github.com/Arjcodes123/OS-Milestone-1`

| Name | ERP |
|---|---|
| Abdul Rehman Javaid | 30532 |
| Hamza Uzair | 30544 |
| Javeria Khan | 31662 |
| Qurat Ul Ain | 30565 |

**Division of work:** all four team members performed the environment setup
(cloning the repository, installing the toolchain, and confirming the three
configurations boot) independently on their own laptops.

""")
parts.append(pagebreak())

# ---------------------------------------------------------------- warm-up
warmup = read("warmup_call_graph.md")
warmup = warmup.replace("# Warm-Up: Call Graph Recovered from `warmup/build/challenge`",
                         "# Warm-Up (Section 3.0)")
warmup = insert_image_after_nth_mermaid(warmup, [(0, "screenshots/warmup_call_graph.png",
                                                    "Recovered call graph for compute()")])
warmup += img("screenshots/gdb_kernel_trace.png",
              "Kernel entry-point trace: gdb break at sys\\_exec, backtrace, registers, stepi (Section 2.10 / reverse-engineering workflow)")
warmup += "\n\nRaw disassembly evidence backing the call graph above is in `docs/figures/warmup_disassembly_evidence.txt` and the full gdb session in `docs/transcripts/gdb_kernel_trace.txt`.\n"
parts.append(warmup)
parts.append(pagebreak())

# ---------------------------------------------------------------- runbook + bring-up evidence
runbook = read("runbook.md")
parts.append(runbook)
parts.append(pagebreak())

parts.append("# Bring-Up Evidence (Section 3.1)\n\n"
             "One console transcript per configuration, as booted following the runbook above.\n")
parts.append("\n## Single Node\n")
parts.append(img("screenshots/single_node_transcript.png", "Single-node bring-up: generated text and profiling report"))
parts.append("\n## Multi-Node Ring (2 workers)\n")
parts.append(img("screenshots/ring_2workers_transcript.png", "Ring bring-up: worker registration through generated text"))
parts.append("\n## Weight-Fetch Path\n")
parts.append(img("screenshots/weightfetch_transcript.png", "testftp: byte counts for tokenizer and weights"))
parts.append(pagebreak())

parts.append("# Regression Suites\n\n")
parts.append(img("screenshots/kernel_regression_test.png", "server/kernel\\_regression\\_test.py -- 14/14 passed, matching the expected table"))
parts.append(img("screenshots/weightfetch_regression_test.png", "server/weightfetch\\_regression\\_test.py -- 4/4 passed, matching the expected table"))
parts.append(img("screenshots/distinf_regression_test.png",
              "server/distinf\\_regression\\_test.py -- failed reproducibly (3/3 attempts) with the same environment-level multicast flakiness; see Observations Log #1 and #5 and Contributions #4. A manual distinf\\_sim.py invocation with identical arguments succeeded and reproduced the single-node token stream exactly (see Bring-Up Evidence above)."))
parts.append(pagebreak())

# ---------------------------------------------------------------- architecture map
arch = read("architecture_map.md")
arch = arch.replace("# Architecture Map", "# Architecture Map (Section 3.3)")
parts.append(arch)
parts.append(pagebreak())

# ---------------------------------------------------------------- figures F1-F7
parts.append("# Figures (Section 3.4)\n")

f1 = read("f1_system_architecture.md")
f1 = insert_image_after_nth_mermaid(f1, [(0, "screenshots/f1_system_architecture.png", "F1: System architecture")])
parts.append(f1); parts.append(pagebreak())

f2 = read("f2_wire_format.md")
f2 = insert_image_after_nth_mermaid(f2, [(0, "screenshots/f2_wire_format.png", "F2: PROC\\_INFER\\_REQ wire format")])
parts.append(f2); parts.append(pagebreak())

f3 = read("f3_worker_lifecycle.md")
f3 = insert_image_after_nth_mermaid(f3, [(0, "screenshots/f3_worker_lifecycle.png", "F3: Worker lifecycle state machine")])
parts.append(f3); parts.append(pagebreak())

f4 = read("f4_token_sequence.md")
f4 = insert_image_after_nth_mermaid(f4, [(0, "screenshots/f4_token_sequence.png", "F4: One token, master through each worker and back")])
parts.append(f4); parts.append(pagebreak())

f5 = read("f5_inference_hot_path.md")
f5 = insert_image_after_nth_mermaid(f5, [(0, "screenshots/f5_inference_hot_path.png", "F5: Inference hot path through llama\\_core.c")])
parts.append(f5); parts.append(pagebreak())

f6 = read("f6_memory_map.md")
f6 = insert_image_after_nth_mermaid(f6, [(0, "screenshots/f6_memory_map.png", "F6: Node memory map, physical and virtual")])
parts.append(f6); parts.append(pagebreak())

f7 = read("f7_baseline_graphs.md")
f7 = insert_image_after_nth_mermaid(f7, [
    (0, "screenshots/f7a_singlenode.png", "F7a: Single-node inference time by prompt"),
    (1, "screenshots/f7b_ring_vs_singlenode.png", "F7b: Generation time, single-node vs. ring"),
    (2, "screenshots/f7c_compute_vs_network.png", "F7c: Per-token compute vs. network breakdown"),
])
parts.append(f7); parts.append(pagebreak())

# ---------------------------------------------------------------- syscall diff
sd = read("syscall_diff.md")
parts.append(sd)
parts.append(pagebreak())

# ---------------------------------------------------------------- baseline measurements
bm = read("baseline_measurements.md")
bm = bm.replace("# Baseline Measurements (Section 3.6)", "# Baseline Measurements (Section 3.6)")
bm += img("screenshots/cycle_instret_probe.png", "gdb probe: cycle/instret CSRs sampled while the vCPU was provably halted")
bm += img("screenshots/baseline_singlenode.png", "Raw console output backing the single-node baseline table")
bm += img("screenshots/baseline_ring_3workers.png", "Raw console output backing the 3-worker ring baseline row")
parts.append(bm)
parts.append(pagebreak())

# ---------------------------------------------------------------- observations log
ol = read("observations_log.md")
parts.append(ol)
parts.append(pagebreak())

# ---------------------------------------------------------------- related systems
rs = read("related_systems.md")
parts.append(rs)
parts.append(pagebreak())

# ---------------------------------------------------------------- contributions
co = read("contributions.md")
parts.append(co)
parts.append(pagebreak())

# ---------------------------------------------------------------- appendices
parts.append(r"""# Appendices

## AI Use Disclosure

This milestone's environment setup, system bring-up, reverse-engineering (warm-up
call graph and kernel gdb trace), architecture mapping, all seven Mermaid figures,
the syscall diff, the baseline-measurement methodology and its execution, the
observations log, the related-systems comparison, and the drafting of this report
were carried out using **Claude Code** (Anthropic), operating the toolchain (QEMU,
gdb, pytest, LaTeX, mermaid-cli) directly inside a WSL2 Ubuntu environment under
the direction and supervision of the team. Every quantitative claim in this report
(regression suite pass counts, baseline timings, syscall numbers, line/address
citations) was produced by actually running the referenced command against this
repository's shipped binaries and source, not generated from general knowledge --
the raw transcripts backing each claim are committed alongside this report under
`docs/transcripts/` and `docs/screenshots/`.

## Repository Layout of Supporting Evidence

- `docs/figures/` -- Markdown source for every report section, and `mmd/` holding
  each Mermaid diagram's standalone source file.
- `docs/screenshots/` -- rendered PNGs: all seven figures plus every console
  transcript, rendered as a terminal-styled image via `docs/tools/termshot.py`.
- `docs/transcripts/` -- raw, unedited console/pytest/gdb output for every run
  referenced in this report.
- `docs/tools/` -- `termshot.py` (transcript-to-image renderer) and
  `gdb_trace_cmds.gdb` (the batch script used for the kernel reverse-engineering
  trace).

## Commit Log

See the repository's `git log` on `https://github.com/Arjcodes123/OS-Milestone-1`
for the commit history backing this submission.
""")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("".join(parts))

print(f"wrote {OUT}, {sum(len(p) for p in parts)} chars")
