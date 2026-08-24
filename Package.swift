// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "VicinusAIApp",
    platforms: [.macOS(.v13)],
    targets: [
        .executableTarget(
            name: "VicinusAIApp",
            path: "Sources/VicinusAIApp"
        )
    ]
)
