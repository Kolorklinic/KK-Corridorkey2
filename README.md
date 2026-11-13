# CorridorKey 2 for Resolve

**Corridor Digital's AI green-screen keyer in DaVinci Resolve, on your Mac.** An OpenFX plugin for Resolve's Fusion and Edit pages and Fusion Studio that keys green and blue screens with [CorridorKey 2.0](https://github.com/nikopueringer/CorridorKey2.0) by Corridor Digital, running on the Mac's own GPU. Hair, fur, motion blur and uneven screens key cleanly with no keyer settings, and a rough garbage matte on its Hint input removes anything outside the screen.

From [Creative Video Tips](https://creativevideotips.com), created by Chadwick. Always free. This is an unofficial plugin, not made or endorsed by Corridor Digital or Blackmagic Design. CorridorKey 2.0 itself runs on NVIDIA graphics cards; this plugin brings it to Apple Silicon Macs.

## Download

### [Download the installer: CorridorKey2-1.00.pkg](https://github.com/creativevideotips/cvt-corridorkey2/releases/download/v1.00/CorridorKey2-1.00.pkg)

### [Download the guide (PDF)](https://github.com/creativevideotips/cvt-corridorkey2/releases/download/v1.00/CorridorKey2_Guide.pdf)

![A green-screen shot of a dog, and the same frame keyed by CorridorKey 2 over a checkerboard](corridorkey2_example.jpg)

## Is it for you?

- **Mac with Apple Silicon only** (M1 or later). There is no Windows, Intel or NVIDIA version of this plugin.
- **64 GB of memory or more.** It uses as much as the Mac can spare: about 24 GB at HD on a 64 GB Mac, up to about 80 GB on a 128 GB one.
- **macOS 14 (Sonoma) or later.**
- **About 7 GB of disk** for CorridorKey and its Python, plus about 2.5 MB for each processed HD frame.
- **Resolve Studio or Fusion Studio.** Tested on Resolve's Fusion and Edit pages and in Fusion Studio.

## Install

1. Quit Resolve and Fusion Studio.
2. Open the downloaded **CorridorKey2-1.00.pkg** and follow the Installer. It is signed and notarized by Apple, and asks for your Mac's password because plugins go in `/Library/OFX/Plugins`.
3. Start Resolve, add **Effects > OpenFX > Creative Video Tips > CorridorKey 2** to a clip, open the node's **Setup** section and press **Install Model**. Terminal opens, asks you to accept the CorridorKey licence, then downloads CorridorKey 2.0's code from Corridor's GitHub and its weights from Hugging Face (about 5 GB), checks every file against the version this plugin was tested with, and loads the model once. You do this once per Mac.

No account or token is needed.

## Using it

Put CorridorKey 2 after your clip and press **Process**. A progress window shows the frame, the chunk and the time left; Status says the same in the Inspector. The node then draws from the stored results, so playback is instant and **Output** and **Despill** change live.

- **Input Is:** Rec.709 for most timelines, sRGB Linear for linear footage, ACEScg for CG renders (the output stays in ACEScg).
- **Temporal Chunks:** how many frames CorridorKey keys together. Auto picks the longest the Mac's memory allows; Status reports what it used ("2 chunks of 80 frames").
- **Output:** Premultiplied, Matte Only, Unpremultiplied (the cleaned foreground with the matte as alpha), or Source + Matte (Unpremultiplied) (your untouched picture with the matte as alpha).
- **Hint:** a rough matte of the subject (a rectangle, Magic Mask or roto) on the Hint input, or in the source's alpha on the Edit page. At a strength of 0.3 to 0.5 it removes anything outside it and keeps CorridorKey's own edges.
- **Frames that aren't processed** show the picture in diagonal stripes with a red frame; a yellow frame means the picture changed since Process. Scrub once before you deliver.
- **Edit page:** after Process, move the playhead once to see the result.

The guide has the details.

## Speed

Measured on HD shots:

| Mac | Seconds per HD frame |
|---|---|
| M5 Max | about 1 |
| M2 Max (64 GB) | about 3.5 |
| M1 Max (64 GB) | about 5 |

## What's where

| | |
|---|---|
| `/Library/OFX/Plugins/CorridorKey2.ofx.bundle` | the plugin |
| `~/CorridorKey` | CorridorKey 2.0, its weights and its Python (Install Model) |
| `~/.cache/cvt-corridorkey2` | stored results and logs (the node's Cache Folder can move the results to any drive, a shared one included) |

To uninstall, delete those three.

## Building from source

You need the Xcode Command Line Tools and cmake. `./build.sh` builds OpenEXR and Imath once (pinned and checksummed), then the plugin into `build/CorridorKey2.ofx.bundle`, and runs the tests. The worker (`worker/`) is Python and runs CorridorKey 2.0 unmodified from the user's `~/CorridorKey` folder, redirecting its CUDA calls to the Apple GPU at runtime.

## Licences

This plugin is licensed under CC BY-NC-SA 4.0 with the CorridorKey additional terms; see [LICENSE](LICENSE). It is free and must stay free. CorridorKey 2.0 and its weights are by Corridor Digital and are downloaded from their own pages under their licence. Organisations with more than US $20 million in annual revenue need a CorridorKey seat for each user from [corridorkey.com](https://corridorkey.com). The components included in the plugin, and the models CorridorKey uses, are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
