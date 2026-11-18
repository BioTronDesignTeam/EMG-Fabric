// Host packets: encode, streaming parser with resync, payloads, and the
// golden file shared with the Python tests (test/golden/host_packets_v2.txt).
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unity.h>

#include <string>
#include <vector>

#include "host_packet.h"

using namespace emg;

void setUp() {}
void tearDown() {}

#ifndef GOLDEN_FILE
#define GOLDEN_FILE "test/golden/host_packets_v2.txt"
#endif

// ---- helpers -------------------------------------------------------------------

static std::vector<uint8_t> from_hex(const std::string& hex) {
    std::vector<uint8_t> out;
    for (size_t i = 0; i + 1 < hex.size(); i += 2) {
        out.push_back(static_cast<uint8_t>(strtoul(hex.substr(i, 2).c_str(), nullptr, 16)));
    }
    return out;
}

static std::vector<long> int_list(const std::string& s) {
    std::vector<long> out;
    size_t start = 0;
    while (start < s.size()) {
        size_t comma = s.find(',', start);
        if (comma == std::string::npos) comma = s.size();
        out.push_back(strtol(s.substr(start, comma - start).c_str(), nullptr, 10));
        start = comma + 1;
    }
    return out;
}

struct GoldenCase {
    std::vector<std::pair<std::string, std::string> > kv;
    bool has(const std::string& k) const {
        for (size_t i = 0; i < kv.size(); ++i) if (kv[i].first == k) return true;
        return false;
    }
    std::string get(const std::string& k) const {
        for (size_t i = 0; i < kv.size(); ++i) if (kv[i].first == k) return kv[i].second;
        TEST_FAIL_MESSAGE(k.c_str());
        return "";
    }
    unsigned long num(const std::string& k) const { return strtoul(get(k).c_str(), nullptr, 10); }
};

static std::vector<GoldenCase> load_golden() {
    std::vector<GoldenCase> cases;
    FILE* f = fopen(GOLDEN_FILE, "r");
    TEST_ASSERT_NOT_NULL_MESSAGE(f, "cannot open " GOLDEN_FILE);
    static char line[8192];
    while (fgets(line, sizeof(line), f)) {
        if (line[0] == '#' || line[0] == '\n') continue;
        GoldenCase c;
        for (char* tok = strtok(line, " \r\n"); tok; tok = strtok(nullptr, " \r\n")) {
            char* eq = strchr(tok, '=');
            if (!eq) continue;
            *eq = '\0';
            c.kv.push_back(std::make_pair(std::string(tok), std::string(eq + 1)));
        }
        cases.push_back(c);
    }
    fclose(f);
    return cases;
}

static std::vector<HostPacket> parse_all(HostPacketParser& p, const std::vector<uint8_t>& bytes) {
    std::vector<HostPacket> out;
    HostPacket pkt;
    for (size_t i = 0; i < bytes.size(); ++i) {
        p.feed(bytes[i]);
        while (p.next(&pkt)) out.push_back(pkt);
    }
    return out;
}

// ---- golden file ---------------------------------------------------------------

static void check_fields(const GoldenCase& c, const HostPacket& pkt) {
    uint8_t rebuilt[kHostMaxPayload];
    if (pkt.type == kPktData) {
        DataPayload d;
        TEST_ASSERT_TRUE(parse_data_payload(pkt.payload, pkt.len, &d));
        TEST_ASSERT_EQUAL_UINT32(c.num("tick"), d.tick);
        TEST_ASSERT_EQUAL(c.num("mask"), d.slot_mask);
        for (int s = 0; s < 4; ++s) {
            if (!(d.slot_mask & (1 << s))) continue;
            const std::string pre = "s" + std::to_string(s) + "_";
            TEST_ASSERT_EQUAL(c.num(pre + "flags"), d.slots[s].flags);
            TEST_ASSERT_EQUAL_UINT32(c.num(pre + "first"), d.slots[s].first_frame);
            const std::vector<long> want = int_list(c.get(pre + "samples"));
            for (size_t i = 0; i < 10; ++i) TEST_ASSERT_EQUAL_INT16(want[i], d.slots[s].samples[i]);
        }
        TEST_ASSERT_EQUAL(pkt.len, build_data_payload(d, rebuilt, sizeof(rebuilt)));
        TEST_ASSERT_EQUAL_MEMORY(pkt.payload, rebuilt, pkt.len);
    } else if (pkt.type == kPktStatus) {
        StatusPayload s;
        TEST_ASSERT_TRUE(parse_status_payload(pkt.payload, pkt.len, &s));
        TEST_ASSERT_EQUAL_UINT32(c.num("uptime"), s.uptime_ms);
        TEST_ASSERT_EQUAL(c.num("present"), s.present_mask);
        const std::vector<long> crc = int_list(c.get("crc_errors")), gaps = int_list(c.get("gaps")),
                                ovr = int_list(c.get("overruns")), fl = int_list(c.get("last_flags"));
        for (int i = 0; i < 4; ++i) {
            TEST_ASSERT_EQUAL_UINT32(crc[i], s.slots[i].crc_errors);
            TEST_ASSERT_EQUAL_UINT32(gaps[i], s.slots[i].gaps);
            TEST_ASSERT_EQUAL_UINT32(ovr[i], s.slots[i].overruns);
            TEST_ASSERT_EQUAL(fl[i], s.slots[i].last_flags);
        }
        TEST_ASSERT_EQUAL(pkt.len, build_status_payload(s, rebuilt, sizeof(rebuilt)));
        TEST_ASSERT_EQUAL_MEMORY(pkt.payload, rebuilt, pkt.len);
    }
}

static void test_golden_file() {
    const std::vector<GoldenCase> cases = load_golden();
    TEST_ASSERT_TRUE(cases.size() >= 8);
    for (size_t i = 0; i < cases.size(); ++i) {
        const GoldenCase& c = cases[i];
        const std::string name = c.get("case");
        const std::vector<uint8_t> bytes = from_hex(c.get("hex"));
        HostPacketParser parser;
        const std::vector<HostPacket> pkts = parse_all(parser, bytes);

        if (c.has("stream")) {
            const std::vector<long> seqs = int_list(c.get("expect_seqs"));
            TEST_ASSERT_EQUAL_MESSAGE(seqs.size(), pkts.size(), name.c_str());
            for (size_t k = 0; k < seqs.size(); ++k) TEST_ASSERT_EQUAL(seqs[k], pkts[k].seq);
            TEST_ASSERT_EQUAL_MESSAGE(c.num("expect_crc_errors"), parser.crc_errors(), name.c_str());
        } else if (c.num("valid") == 0) {
            TEST_ASSERT_EQUAL_MESSAGE(0, pkts.size(), name.c_str());
        } else {
            TEST_ASSERT_EQUAL_MESSAGE(1, pkts.size(), name.c_str());
            const HostPacket& p = pkts[0];
            TEST_ASSERT_EQUAL_MESSAGE(c.num("type"), p.type, name.c_str());
            TEST_ASSERT_EQUAL_MESSAGE(c.num("seq"), p.seq, name.c_str());
            const std::vector<uint8_t> payload = from_hex(c.get("payload"));
            TEST_ASSERT_EQUAL_MESSAGE(payload.size(), p.len, name.c_str());
            if (!payload.empty()) TEST_ASSERT_EQUAL_MEMORY(payload.data(), p.payload, p.len);
            check_fields(c, p);

            // The C encoder must produce exactly the golden bytes.
            uint8_t enc[kHostMaxPacket];
            const size_t n = encode_host_packet(p.type, p.seq, p.payload, p.len, enc, sizeof(enc));
            TEST_ASSERT_EQUAL_MESSAGE(bytes.size(), n, name.c_str());
            TEST_ASSERT_EQUAL_MEMORY_MESSAGE(bytes.data(), enc, n, name.c_str());
        }
    }
}

// ---- hand-written cases --------------------------------------------------------

static void test_many_back_to_back_packets() {
    std::vector<uint8_t> stream;
    for (uint16_t s = 0; s < 50; ++s) {
        DataPayload d;
        memset(&d, 0, sizeof(d));
        d.tick = s * 10u;
        d.slot_mask = 0x0F;  // all 4 slots: the largest DATA packet
        uint8_t pl[kHostMaxPayload], pkt[kHostMaxPacket];
        const size_t pn = build_data_payload(d, pl, sizeof(pl));
        TEST_ASSERT_EQUAL(105, pn);
        const size_t n = encode_host_packet(kPktData, s, pl, static_cast<uint16_t>(pn), pkt, sizeof(pkt));
        stream.insert(stream.end(), pkt, pkt + n);
    }
    HostPacketParser p;
    const std::vector<HostPacket> got = parse_all(p, stream);
    TEST_ASSERT_EQUAL(50, got.size());
    for (uint16_t s = 0; s < 50; ++s) TEST_ASSERT_EQUAL(s, got[s].seq);
    TEST_ASSERT_EQUAL(0, p.crc_errors());
}

static void test_impossible_length_is_skipped_at_once() {
    // A header claiming len=257 can't be real: skip it at once instead of
    // waiting for 257 bytes.
    std::vector<uint8_t> bytes;
    const uint8_t junk[] = {0xAA, 0x55, kHostVersion, 1, 0, 0, 0x01, 0x01};
    bytes.insert(bytes.end(), junk, junk + sizeof(junk));
    uint8_t good[16];
    const size_t n = encode_host_packet(kPktLog, 9, nullptr, 0, good, sizeof(good));
    bytes.insert(bytes.end(), good, good + n);
    HostPacketParser p;
    const std::vector<HostPacket> got = parse_all(p, bytes);
    TEST_ASSERT_EQUAL(1, got.size());
    TEST_ASSERT_EQUAL(9, got[0].seq);
}

static void test_bad_payload_lengths_rejected() {
    uint8_t buf[64] = {0};
    DataPayload d;
    StatusPayload s;
    buf[4] = 0x01;  // one slot claimed but no slot bytes
    TEST_ASSERT_FALSE(parse_data_payload(buf, 5, &d));
    buf[4] = 0x10;  // slot 5 doesn't exist
    TEST_ASSERT_FALSE(parse_data_payload(buf, 5, &d));
    TEST_ASSERT_FALSE(parse_status_payload(buf, 56, &s));
}

int main() {
    UNITY_BEGIN();
    RUN_TEST(test_golden_file);
    RUN_TEST(test_many_back_to_back_packets);
    RUN_TEST(test_impossible_length_is_skipped_at_once);
    RUN_TEST(test_bad_payload_lengths_rejected);
    return UNITY_END();
}
