/* -*- P4_16 -*- */
/*
 * Basic L2 Forwarding Switch
 * 
 * This is the simplest possible P4 program for our demo:
 * - Matches on ingress port
 * - Forwards to the specified egress port
 * - Includes a packet counter register for telemetry
 */

#include <core.p4>
#include <v1model.p4>

/*************************************************************************
 ***********************  H E A D E R S  *********************************
 *************************************************************************/

typedef bit<48> macAddr_t;
typedef bit<9>  port_t;

header ethernet_t {
    macAddr_t dstAddr;
    macAddr_t srcAddr;
    bit<16>   etherType;
}

struct metadata_t {
    /* empty for now */
}

struct headers_t {
    ethernet_t ethernet;
}

/*************************************************************************
 ***********************  P A R S E R  ***********************************
 *************************************************************************/

parser MyParser(packet_in packet,
                out headers_t hdr,
                inout metadata_t meta,
                inout standard_metadata_t standard_metadata) {

    state start {
        packet.extract(hdr.ethernet);
        transition accept;
    }
}

/*************************************************************************
 ************   C H E C K S U M    V E R I F I C A T I O N   *************
 *************************************************************************/

control MyVerifyChecksum(inout headers_t hdr, inout metadata_t meta) {
    apply { }
}

/*************************************************************************
 **************  I N G R E S S   P R O C E S S I N G   *******************
 *************************************************************************/

control MyIngress(inout headers_t hdr,
                  inout metadata_t meta,
                  inout standard_metadata_t standard_metadata) {

    // Counter register: tracks packets per port (for telemetry)
    register<bit<32>>(256) packet_counter;
    
    // Drop counter: tracks dropped packets
    register<bit<32>>(1) drop_counter;

    action drop() {
        // Increment drop counter
        bit<32> count;
        drop_counter.read(count, 0);
        drop_counter.write(0, count + 1);
        
        mark_to_drop(standard_metadata);
    }

    action forward(port_t port) {
        // Increment packet counter for this port
        bit<32> count;
        packet_counter.read(count, (bit<32>)standard_metadata.ingress_port);
        packet_counter.write((bit<32>)standard_metadata.ingress_port, count + 1);
        
        // Set egress port
        standard_metadata.egress_spec = port;
    }

    table forward_table {
        key = {
            standard_metadata.ingress_port: exact;
        }
        actions = {
            forward;
            drop;
        }
        size = 256;
        default_action = drop();
    }

    apply {
        forward_table.apply();
    }
}

/*************************************************************************
 ****************  E G R E S S   P R O C E S S I N G   *******************
 *************************************************************************/

control MyEgress(inout headers_t hdr,
                 inout metadata_t meta,
                 inout standard_metadata_t standard_metadata) {
    apply { }
}

/*************************************************************************
 *************   C H E C K S U M    C O M P U T A T I O N   **************
 *************************************************************************/

control MyComputeChecksum(inout headers_t hdr, inout metadata_t meta) {
    apply { }
}

/*************************************************************************
 ***********************  D E P A R S E R  *******************************
 *************************************************************************/

control MyDeparser(packet_out packet, in headers_t hdr) {
    apply {
        packet.emit(hdr.ethernet);
    }
}

/*************************************************************************
 ***********************  S W I T C H  ***********************************
 *************************************************************************/

V1Switch(
    MyParser(),
    MyVerifyChecksum(),
    MyIngress(),
    MyEgress(),
    MyComputeChecksum(),
    MyDeparser()
) main;
