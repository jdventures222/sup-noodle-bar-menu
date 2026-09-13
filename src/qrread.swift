import Foundation
import Vision
import AppKit
for path in CommandLine.arguments.dropFirst() {
  guard let img = NSImage(contentsOfFile: path), let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { print("\(path): unreadable"); continue }
  let req = VNDetectBarcodesRequest(); req.symbologies = [.qr]
  try! VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
  let r = req.results ?? []
  print("\(path): \(r.count) code(s) -> \(r.map { $0.payloadStringValue ?? "?" })")
}
