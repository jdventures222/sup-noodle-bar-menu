import Foundation
import CoreImage
import AppKit

// Usage: qr <url> <out.png> <size px> [logo.png]
let a = CommandLine.arguments
let url = a[1], out = a[2], size = Int(a[3]) ?? 2048
let logoPath = a.count > 4 ? a[4] : nil
let f = CIFilter(name: "CIQRCodeGenerator")!
f.setValue(url.data(using: .utf8)!, forKey: "inputMessage")
f.setValue("H", forKey: "inputCorrectionLevel")
let code = f.outputImage!
let modules = Int(code.extent.width)            // includes a 1-module border from CoreImage
let quiet = 4                                    // extra quiet zone in modules
let px = size / (modules + 2 * quiet)            // integer pixels per module keeps edges crisp
let codePx = px * modules, canvasPx = px * (modules + 2 * quiet)
let scaled = code.samplingNearest().transformed(by: CGAffineTransform(scaleX: CGFloat(px), y: CGFloat(px)))
let ctx = CIContext(options: nil)
let cg = ctx.createCGImage(scaled, from: CGRect(x: 0, y: 0, width: codePx, height: codePx))!
let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: canvasPx, pixelsHigh: canvasPx, bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
NSGraphicsContext.saveGraphicsState()
let g = NSGraphicsContext(bitmapImageRep: rep)!
NSGraphicsContext.current = g
g.imageInterpolation = .none
NSColor.white.setFill(); NSRect(x: 0, y: 0, width: canvasPx, height: canvasPx).fill()
g.cgContext.draw(cg, in: CGRect(x: px * quiet, y: px * quiet, width: codePx, height: codePx))
if let lp = logoPath, let logo = NSImage(contentsOfFile: lp) {
  // Level H tolerates ~30% damage; the logo covers ~4.5% of the area (21% of the width).
  let d = CGFloat(canvasPx) * 0.21, ring = d * 0.07
  let c = CGFloat(canvasPx) / 2
  NSColor.white.setFill(); NSBezierPath(ovalIn: NSRect(x: c - d / 2 - ring, y: c - d / 2 - ring, width: d + 2 * ring, height: d + 2 * ring)).fill()
  g.imageInterpolation = .high
  let clip = NSBezierPath(ovalIn: NSRect(x: c - d / 2, y: c - d / 2, width: d, height: d)); clip.addClip()
  logo.draw(in: NSRect(x: c - d / 2, y: c - d / 2, width: d, height: d), from: .zero, operation: .sourceOver, fraction: 1)
}
NSGraphicsContext.restoreGraphicsState()
try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: out))
print("wrote \(out) \(canvasPx)x\(canvasPx) modules=\(modules) px/module=\(px)")
