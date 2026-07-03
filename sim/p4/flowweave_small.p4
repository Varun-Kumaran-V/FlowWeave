// sim/p4/flowweave_small.p4
// P4_16 skeleton for FlowWeave detection + marking (conceptual)

#include <core.p4>

const bit<32> DERIV_THRESHOLD = 5000; // will be configured by controller
const bit<32> TCAM_LIMIT = 2000;
const bit<32> REPORT_INTERVAL_MS = 10; // not used directly in P4

// Header definitions (IPv4/TCP simplified)
header ethernet_t { bit<48> dst; bit<48> src; bit<16> eth_type; }
header ipv4_t { bit<4> ver; bit<4> ihl; bit<8> diff; bit<16> len; bit<16> id; bit<3> flags; bit<13> frag; bit<8> ttl; bit<8> protocol; bit<16> hdr_checksum; bit<32> src; bit<32> dst; }
header tcp_t { bit<16> srcPort; bit<16> dstPort; bit<32> seqNo; bit<32> ackNo; bit<4> dataOffset; bit<4> res; bit<8> flags; bit<16> window; bit<16> checksum; bit<16> urgentPtr; }

struct metadata {
    bit<1> detect;
    bit<32> flow_hash;
    bit<32> slot_idx;
}

parser MyParser(packet_in pkt, out headers hdr, inout metadata meta, inout standard_metadata_t stdmeta) {
    state start {
        pkt.extract(hdr.ethernet);
        transition select(hdr.ethernet.eth_type) {
            0x0800: parse_ipv4;
            default: accept;
        }
    }
    state parse_ipv4 {
        pkt.extract(hdr.ipv4);
        transition select(hdr.ipv4.protocol) {
            6: parse_tcp;
            default: accept;
        }
    }
    state parse_tcp {
        pkt.extract(hdr.tcp);
        transition accept;
    }
}

control ingress(inout headers hdr, inout metadata meta, inout standard_metadata_t stdmeta) {
    // registers
    // slot_count[slot] accumulates per ms counts (small sliding window implemented by controller advancing slot pointer)
    register<bit<32>>(1024) slot_count; // number of slots is small; index via slot_idx
    register<bit<32>>(1) ewma_reg; // EWMA per-switch simplified
    // superflow_active flag (controller-managed)
    register<bit<1>>(1) superflow_active;

    action no_op() {}

    // action to update counters and ewma
    action update_and_detect(bit<32> slot, bit<32> flowhash) {
        bit<32> prev = slot_count.read(slot);
        slot_count.write(slot, prev + 1);
        // read ewma
        bit<32> old_ewma = ewma_reg.read(0);
        // EWMA with alpha = 1/8 approximate: new = old - old/8 + count/8
        bit<32> old_div8 = old_ewma >> 3;
        bit<32> add_div8 = (prev + 1) >> 3;
        bit<32> new_ewma = old_ewma - old_div8 + add_div8;
        ewma_reg.write(0, new_ewma);

        bit<32> deriv = (prev + 1) > new_ewma ? (prev + 1) - new_ewma : 0;
        bit<1> active = superflow_active.read(0);
        if (deriv >= DERIV_THRESHOLD && active == 0) {
            meta.detect = 1;
        } else {
            meta.detect = 0;
        }
    }

    table update_table {
        key = {
            // match on nothing; apply for all packets
        }
        actions = { update_and_detect; no_op; }
        size = 1;
        default_action = no_op();
    }

    apply {
        // compute flow hash simple
        meta.flow_hash = (bit<32>) (hash(hdr.ipv4.src, hdr.ipv4.dst, hdr.tcp.srcPort, hdr.tcp.dstPort) & 0xffffffff);
        // slot index - controller rotates slot pointer via register writes; here assume slot 0
        meta.slot_idx = 0;
        update_table.apply();
        if (meta.detect == 1) {
            // mark packet for controller digest (Packet-in / digest) or set metadata for cloning to CPU port
            // in P4Runtime you’d send a digest to controller
            // We'll set a register or clone to CPU - controller must handle.
            // Example: clone to CPU port
            // clone_ingress_packet_to_egress(<cpu_port>);
        }
    }
}

control egress(...) { apply { } }
control verify_checksum(...) { apply { } }
control compute_checksum(...) { apply { } }
V1Switch(MyParser(), ingress(), egress(), verify_checksum(), compute_checksum()) main;