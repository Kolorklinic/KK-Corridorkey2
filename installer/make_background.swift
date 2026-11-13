// ---------------------------------------------------------------------------
// cvtCorridorKey2 installer/make_background.swift
//
// From Creative Video Tips (CVT) - CorridorKey 2 for Resolve (copied from
// LTX Alpha Gen's installer, where CVT wrote it).
//
// What it does:
//   Makes the installer's background image: the CVT logo, trimmed to its
//   visible pixels, on a transparent canvas, so the Installer window shows it
//   in its lower-left corner (package.sh places it with alignment
//   "bottomleft", no scaling). Writes a 1x and a 2x PNG; join
//   them into one Retina TIFF with tiffutil, in installer/resources/:
//     swift make_background.swift ../../cvt_logo/cvt_app_logo_dark_grey.png l.png l@2x.png
//     tiffutil -cathidpicheck l.png l@2x.png -out resources/background_light.tiff
//   and the same with cvt_app_logo_white.png for resources/background_dark.tiff (Dark Mode).
//
//   swift make_background.swift <logo.png> <out-1x.png> <out-2x.png>
// ---------------------------------------------------------------------------
import AppKit
import CoreGraphics

let canvasW = 200.0, canvasH = 120.0  // points: the area below the step list
let logoW = 120.0                      // the logo's width in points
let marginX = 30.0, marginY = 28.0     // from the window's left and bottom edges

let args = CommandLine.arguments
guard args.count == 4, let src = NSImage(contentsOfFile: args[1]),
      let cg = src.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
  FileHandle.standardError.write("usage: make_background.swift <logo.png> <out-1x.png> <out-2x.png>\n".data(using: .utf8)!)
  exit(2)
}

// The logo's visible pixels (alpha > 0): the PNG has empty space around it.
func trimmed(_ img: CGImage) -> CGImage {
  let w = img.width, h = img.height
  var px = [UInt8](repeating: 0, count: w * h * 4)
  let ctx = CGContext(data: &px, width: w, height: h, bitsPerComponent: 8, bytesPerRow: w * 4,
                      space: CGColorSpaceCreateDeviceRGB(),
                      bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
  ctx.draw(img, in: CGRect(x: 0, y: 0, width: w, height: h))
  var x0 = w, y0 = h, x1 = -1, y1 = -1
  for y in 0..<h { for x in 0..<w where px[(y * w + x) * 4 + 3] > 0 {
    x0 = min(x0, x); x1 = max(x1, x); y0 = min(y0, y); y1 = max(y1, y)
  } }
  guard x1 >= x0 else { return img }
  // The buffer's rows run top-down, as cropping expects.
  return img.cropping(to: CGRect(x: x0, y: y0, width: x1 - x0 + 1, height: y1 - y0 + 1)) ?? img
}

let logo = trimmed(cg)
let logoH = logoW * Double(logo.height) / Double(logo.width)

func write(scale: Double, to path: String) {
  let w = Int(canvasW * scale), h = Int(canvasH * scale)
  let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0,
                      space: CGColorSpace(name: CGColorSpace.sRGB)!,
                      bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
  ctx.interpolationQuality = .high
  ctx.clear(CGRect(x: 0, y: 0, width: w, height: h))
  ctx.draw(logo, in: CGRect(x: marginX * scale, y: marginY * scale, width: logoW * scale, height: logoH * scale))
  let rep = NSBitmapImageRep(cgImage: ctx.makeImage()!)
  rep.size = NSSize(width: canvasW, height: canvasH)  // 72 dpi at 1x, 144 dpi at 2x
  try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: path))
}

write(scale: 1, to: args[2])
write(scale: 2, to: args[3])
print("logo \(logo.width)x\(logo.height) px -> \(Int(logoW))x\(Int(logoH.rounded())) pt at (\(Int(marginX)), \(Int(marginY)))")
