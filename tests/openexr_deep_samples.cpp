// Licensed under the Apache License, Version 2.0. See LICENSE and NOTICE.
// Bounded public-API regression for CVE-2023-5841; no large allocation or pixel
// unpacking is attempted. All input files are generated in the working directory.
#include <OpenEXR/ImfChannelList.h>
#include <OpenEXR/ImfDeepFrameBuffer.h>
#include <OpenEXR/ImfDeepScanLineOutputFile.h>
#include <OpenEXR/ImfHeader.h>
#include <OpenEXR/ImfPartType.h>
#include <OpenEXR/openexr.h>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
namespace IMF = OPENEXR_IMF_NAMESPACE;
static void require(bool ok, const char* message) {
    if (!ok) throw std::runtime_error(message);
}
static void generate() {
    IMF::Header header(2, 1);
    header.setType(IMF::DEEPSCANLINE);
    header.compression() = IMF::NO_COMPRESSION;
    header.channels().insert("Z", IMF::Channel(IMF::FLOAT));
    unsigned int counts[2] = {2, 1};
    float values[3] = {1, 2, 3};
    float* pixels[2] = {values, values + 2};
    IMF::DeepFrameBuffer frame;
    frame.insertSampleCountSlice(IMF::Slice(IMF::UINT, (char*)counts, 4, 8));
    frame.insert("Z", IMF::DeepSlice(IMF::FLOAT, (char*)pixels,
                 sizeof(float*), 2*sizeof(float*), sizeof(float)));
    IMF::DeepScanLineOutputFile out("deep.exr", header);
    out.setFrameBuffer(frame);
    out.writePixels(1);
}
static exr_result_t decode(unsigned int second, bool individual) {
    generate();
    exr_context_t context = nullptr;
    require(exr_start_read(&context, "deep.exr", nullptr) == EXR_ERR_SUCCESS, "open");
    exr_chunk_info_t chunk{};
    require(exr_read_scanline_chunk_info(context, 0, 0, &chunk) == EXR_ERR_SUCCESS, "chunk");
    require(chunk.sample_count_table_size == 8, "bounded sample table");
    exr_finish(&context);
    // On-disk sample counts are cumulative little-endian integers.
    unsigned char bytes[4];
    for (unsigned i=0; i<4; ++i) bytes[i] = (second >> (8*i)) & 255;
    std::fstream file("deep.exr", std::ios::binary | std::ios::in | std::ios::out);
    file.seekp(chunk.sample_count_data_offset + 4);
    file.write((char*)bytes, 4); file.close();
    require(exr_start_read(&context, "deep.exr", nullptr) == EXR_ERR_SUCCESS, "reopen");
    exr_decode_pipeline_t pipeline{};
    require(exr_decoding_initialize(context, 0, &chunk, &pipeline) == EXR_ERR_SUCCESS, "initialize");
    pipeline.decode_flags = EXR_DECODE_SAMPLE_DATA_ONLY |
        (individual ? EXR_DECODE_SAMPLE_COUNTS_AS_INDIVIDUAL : 0);
    require(exr_decoding_choose_default_routines(context, 0, &pipeline) == EXR_ERR_SUCCESS, "choose");
    if (individual) {
        // 3.1.x's uncompressed default pipeline does not populate the separate
        // individual-count buffer. Use the public transcode hook to copy the
        // tiny uncompressed table; retain the real shared count validator.
        // This does not qualify the default individual-count transport path.
        pipeline.decompress_fn = [](exr_decode_pipeline_t* p) -> exr_result_t {
            if (p->chunk.sample_count_table_size != 8 || p->sample_count_alloc_size < 12)
                return EXR_ERR_INVALID_ARGUMENT;
            std::memcpy(p->sample_count_table, p->packed_sample_count_table, 8);
            return EXR_ERR_SUCCESS;
        };
    }
    auto result = exr_decoding_run(context, 0, &pipeline);
    if (result == EXR_ERR_SUCCESS && second == 3) {
        require(pipeline.sample_count_table[0] == 2, "first count");
        require(pipeline.sample_count_table[1] == (individual ? 1 : 3), "second count");
    }
    exr_decoding_destroy(context, &pipeline);
    exr_finish(&context);
    return result;
}
int main() {
    int failed=0;
    for (bool individual : {false, true}) {
        for (unsigned int second : {3U, 1U, 0xffffffffU}) {
            auto result = decode(second, individual);
            bool ok = second == 3 ? result == EXR_ERR_SUCCESS : result == EXR_ERR_INVALID_SAMPLE_DATA;
            std::cout << (individual ? "individual" : "cumulative") << ":" << second
                      << "=" << (ok ? "PASS" : "FAIL") << " result=" << result << "\n";
            failed += !ok;
        }
    }
    return failed ? 1 : 0;
}
