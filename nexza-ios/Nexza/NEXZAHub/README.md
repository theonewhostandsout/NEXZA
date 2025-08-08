# NEXZA Hub

An iOS SwiftUI app that connects to a locally hosted AI server through a Tailscale IP. It features a minimalist dark chat interface, optional login screen and local chat history persistence.

## Usage

Create a new SwiftUI iOS project in Xcode (iOS 16 +) and copy the contents of the `NEXZAHub` package's `Sources/NEXZAHub` folder into your project. Alternatively, add the package as a local Swift Package if preferred.

Replace the placeholder IP in `AIService.swift` with your own Tailscale address before running. The UI is optimised for iPhone 16 Pro Max but works on all iPhones.

Future versions will include image input support and in‑app alerts.