// ---------------------------------------------------------------------------
// CorridorKey 2 for Resolve - EXR reading and writing (OpenEXR)
//
// From Creative Video Tips (CVT)  |  https://creativevideotips.com
// Licence: CC BY-NC-SA 4.0 with the CorridorKey additional terms (see LICENSE).
//
// Every EXR the plugin and its worker exchange is half float, DWAB
// compression at level 45 (Chadwick's standard): the frames handed to the
// worker and the stored results. DWAB is lossy for R, G, B and lossless for
// A, so the matte keeps every value.
// ---------------------------------------------------------------------------
#pragma once

#include <string>
#include <vector>

namespace ck2 {

constexpr float kDwaLevel = 45.0f;

// Interleaved RGBA float image, top row first.
struct ImageRGBA {
    int width = 0;
    int height = 0;
    std::vector<float> pixels;          // width * height * 4
};

// Writes R,G,B (and A when `withAlpha`) as half float, DWAB level 45.
// `rgba` is interleaved RGBA float with `rowStride` floats between rows, top
// row first (negative stride for bottom-up pictures). Writes to a temporary
// name, then renames. Returns false and sets `error` on failure.
bool writeExr(const std::string& path, const float* rgba, int width, int height,
              long rowStride, std::string& error, bool withAlpha = false);

// Reads any scanline or tiled EXR into RGBA float (missing channels: RGB 0,
// A 1). Returns false and sets `error` on failure.
bool readExrRGBA(const std::string& path, ImageRGBA& out, std::string& error);

}  // namespace ck2
