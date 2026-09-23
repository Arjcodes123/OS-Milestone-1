# F2 — Wire Format: RPC Envelope + XDR Activation Message (packet-beta)

Source: `user/rpc.h` (RFC 5531 §9 `call_body`/`rpc_msg` envelope) and `user/distinf.h`
(`infer_hop_t`, the `PROC_INFER_REQ` payload — one ring-hop activation message). All
multi-byte fields are 32-bit big-endian per RFC 4506 §4.2; the activation array is
IEEE 754 binary32, canonical big-endian, RFC 4506 §4.6/§4.12.

```mermaid
packet-beta
title PROC_INFER_REQ on the wire: RPC envelope (RFC 5531 §9) + XDR activation payload (RFC 4506)
0-31: "xid (transaction id)"
32-63: "mtype = CALL (0)"
64-95: "rpcvers = 2"
96-127: "prog = INFERENCE_PROG"
128-159: "vers = INFERENCE_VERS"
160-191: "proc = PROC_INFER_REQ (4)"
192-223: "cred.flavor = AUTH_NONE (0)"
224-255: "cred.body_len = 0"
256-287: "verf.flavor = AUTH_NONE (0)"
288-319: "verf.body_len = 0"
320-351: "session_id (epoch)"
352-383: "seq (strictly increasing, anti-replay)"
384-415: "pos (token position, RoPE + KV index)"
416-447: "hop (expected handler index)"
448-479: "n_floats (= dim)"
480-511: "flags (bit0 = INFER_FLAG_FINAL)"
512-543: "compute_us (cumulative shard_forward time)"
544-575: "activation[0]  (float32, big-endian, RFC 4506 §4.6/§4.12)"
576-607: "activation[1]  (float32, big-endian)"
608-639: "..."
```

The envelope (xid through verf.body_len, 40 bytes) is identical across every RPC
procedure; only `proc` (word 5) and the payload after it change. The payload here
(`infer_hop_t`, `distinf.h:87-95`, 7 words = 28 bytes) is followed by `n_floats`
activation floats — at `dim=768` that is 3072 bytes of floats, for a total payload of
3100 bytes, deliberately kept under `RPC_PAYLOAD_MAX` (4096, `rpc.h:177`) but above
the 1500-byte Ethernet MTU, so the header comment in `distinf.h:22-25` notes this is
by design: every hop exercises IP fragmentation/reassembly (RFC 791) rather than
leaving that path untested.
