// Licensed under the Apache License, Version 2.0. See LICENSE and NOTICE.
// Bounded synthetic data; exercise the installed library's public constructor.
#include <OpenEXR/ImfIDManifest.h>
#include <OpenEXR/Iex.h>
#include <cstdint>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

using namespace OPENEXR_IMF_NAMESPACE;
using Bytes = std::vector<char>;
static void u32(Bytes& b, uint32_t v) {
    for (unsigned n=0; n<4; ++n) b.push_back(char(v >> (8*n)));
}
static void varint(Bytes& b, uint64_t v) {
    do { unsigned c=v & 127; v >>= 7; b.push_back(char(c | (v ? 128 : 0))); } while(v);
}
static Bytes strings(const std::string& first, const std::string& second) {
    Bytes b; u32(b,0); u32(b,2); varint(b,first.size()); varint(b,second.size());
    b.insert(b.end(),first.begin(),first.end()); b.insert(b.end(),second.begin(),second.end());
    u32(b,0); u32(b,0); return b;
}
static bool rejects(const std::string& name, const Bytes& b, const std::string& message) {
    std::string outcome="accepted";
    bool pass=false;
    try { IDManifest parsed(b.data(),b.data()+b.size()); }
    catch(const IEX_NAMESPACE::InputExc& e) {
        outcome="InputExc";
        pass=std::string(e.what()).find(message)!=std::string::npos;
    }
    catch(const std::exception&) { outcome="other_exception"; }
    std::cout << name << ": " << (pass ? "PASS" : "FAIL") << " (" << outcome << ")\n";
    return pass;
}
int main() {
    int failures=0;
    for (unsigned count : {11u,12u}) {
        Bytes b; u32(b,0); u32(b,1);
        for(unsigned n=1;n<count;++n) b.push_back(char(128));
        b.push_back(0); u32(b,0); u32(b,0);
        failures += !rejects("overlong-varint-"+std::to_string(count),b,
                             "Invalid variable-length integer in IDManifest");
    }
    failures += !rejects("long-prefix-empty",strings(std::string(256,'x'),""),
                         "IDManifest string too small for common prefix length");
    failures += !rejects("long-prefix-one-byte",strings(std::string(256,'x'),std::string(1,0)),
                         "IDManifest string too small for common prefix length");
    failures += !rejects("short-prefix-empty",strings("x",""),
                         "IDManifest string too small for common prefix length");
    Bytes truncated; u32(truncated,0); u32(truncated,1); truncated.push_back(char(128));
    failures += !rejects("truncated-varint",truncated,"IDManifest too small for variable length integer");
    try {
        Bytes b; u32(b,0); u32(b,1);
        for(unsigned n=0;n<9;++n) b.push_back(char(128));
        b.push_back(0); u32(b,0); u32(b,0);
        IDManifest parsed(b.data(),b.data()+b.size());
        std::cout << "representable-10-byte-varint: PASS\n";
    } catch(...) { std::cout << "representable-10-byte-varint: FAIL\n"; ++failures; }
    try {
        IDManifest original; auto& group=original.add("synthetic"); group.setComponent("name");
        group.insert(0,"hello"); group.insert(1,std::string(256,'x')+"a");
        group.insert(std::numeric_limits<uint64_t>::max(),std::string(256,'x')+"b");
        Bytes data; original.serialize(data);
        IDManifest parsed(data.data(),data.data()+data.size());
        if(parsed!=original) throw std::runtime_error("roundtrip mismatch");
        CompressedIDManifest compressed(original); IDManifest decompressed(compressed);
        if(decompressed!=original) throw std::runtime_error("compressed mismatch");
        std::cout << "serialized-and-compressed-roundtrip: PASS\n";
    } catch(...) { std::cout << "serialized-and-compressed-roundtrip: FAIL\n"; ++failures; }
    return failures ? 1 : 0;
}
