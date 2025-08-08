// swift-tools-version: 6.1
// Package description for the NEXZAHub Swift package.

import PackageDescription

let package = Package(
    name: "NEXZAHub",
    platforms: [
        .iOS(.v16)
    ],
    products: [
        // The library exposes the NEXZAHub target for other projects.
        .library(name: "NEXZAHub", targets: ["NEXZAHub"])
    ],
    targets: [
        // The core NEXZAHub target containing the app logic and views.
        .target(name: "NEXZAHub")
    ]
)