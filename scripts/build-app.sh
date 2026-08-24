#!/bin/bash
# Assembles VicinusAI.app from the SwiftPM release build.
set -euo pipefail
cd "$(dirname "$0")/.."

swift build --disable-sandbox -c release

APP=build/VicinusAI.app
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS"
cp .build/release/VicinusAIApp "$APP/Contents/MacOS/VicinusAI"

cat > "$APP/Contents/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>              <string>VicinusAI</string>
    <key>CFBundleDisplayName</key>       <string>VicinusAI</string>
    <key>CFBundleIdentifier</key>        <string>ai.vicinus.VicinusAI</string>
    <key>CFBundleVersion</key>           <string>1.0</string>
    <key>CFBundleShortVersionString</key><string>1.0</string>
    <key>CFBundlePackageType</key>       <string>APPL</string>
    <key>CFBundleExecutable</key>        <string>VicinusAI</string>
    <key>LSMinimumSystemVersion</key>    <string>13.0</string>
    <key>NSHighResolutionCapable</key>   <true/>
    <key>NSPrincipalClass</key>          <string>NSApplication</string>
    <key>NSAppTransportSecurity</key>
    <dict>
        <key>NSAllowsLocalNetworking</key> <true/>
    </dict>
</dict>
</plist>
PLIST

codesign --force --sign - "$APP"
echo "Built $APP"
