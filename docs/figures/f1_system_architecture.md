# F1 — System Architecture (flowchart)

Weight server, master, the N workers, the ring, and the transport between them, drawn
from `server/server.py`, `server/mcast_switch.py`/`boot.sh`'s SLIRP networking, and
`user/distinf.c`'s master/worker roles.

```mermaid
flowchart LR
    subgraph HOST["Host (Linux / server/)"]
        WS["Weight server<br/>server/server.py<br/>UDP :9999, LLM-RFTP"]
        SW["mcast_switch.py<br/>(ring config only: bridges WS<br/>onto the QEMU multicast segment,<br/>answers ARP for 10.0.0.1)"]
    end

    subgraph GUEST0["xv6 node: master"]
        MA["distinf --master<br/>run_master() :1268<br/>registry, layer assignment,<br/>master_run_token per-token loop"]
        LC0["llama_core.c<br/>embedding table + classifier only"]
    end

    subgraph GUEST1["xv6 node: worker 1 (head)"]
        W1["distinf --worker<br/>run_worker() :1392"]
        SH1["shard.c: layers [0,k)"]
        LC1["llama_core.c: llama_block per owned layer"]
    end

    subgraph GUESTN["xv6 node: worker N (tail)"]
        WN["distinf --worker"]
        SHN["shard.c: layers [j,n_layers)"]
        LCN["llama_core.c: llama_block per owned layer"]
    end

    WS -- "LLM-RFTP: tokenizer.bin, stories*.bin<br/>user/ftpclient.c" --> MA
    WS -- LLM-RFTP --> W1
    WS -- LLM-RFTP --> WN
    SW -. "bridges WS onto mcast segment<br/>(multi-worker ring only)" .-> WS

    MA == "PROC_INFER_REQ (ring hop 0)<br/>RPC/UDP, RFC 5531" ==> W1
    W1 == "PROC_INFER_REQ (hop 1)" ==> WN
    WN == "PROC_INFER_REQ (hop N, INFER_FLAG_FINAL)" ==> MA

    MA -. "PROC_AUTH_HELLO / PROC_CAP_ACK<br/>discovery.c registration" .-> W1
    MA -. registration .-> WN
    MA -. "PROC_ASSIGN_LAYERS" .-> W1
    MA -. "PROC_ASSIGN_LAYERS" .-> WN
    W1 -. "PROC_SHARD_READY" .-> MA
    WN -. "PROC_SHARD_READY" .-> MA
```

Solid double arrows: the per-token ring hop path (the hot path, F4/F5). Dashed
arrows: control-plane RPCs (registration, layer assignment, shard-ready) that run
once per session, not once per token. The single-node configuration (`llama.c`) is
the degenerate case of this diagram with zero workers: `llama_core.c` runs every
layer locally and only the weight-server edge exists.
