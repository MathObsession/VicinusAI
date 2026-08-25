#!/bin/bash
# Assembles VicinusAI.app from the SwiftPM release build.
set -euo pipefail
cd "$(dirname "$0")/.."

swift build --disable-sandbox -c release

APP=build/VicinusAI.app
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp .build/release/VicinusAIApp "$APP/Contents/MacOS/VicinusAI"

cp Sources/VicinusAIApp/Resources/StackSansNotch-Regular.ttf "$APP/Contents/Resources/"
cp Sources/VicinusAIApp/Resources/StackSansNotch-Bold.ttf    "$APP/Contents/Resources/"

# App icon from the frontend favicon.
ICONDIR="$(mktemp -d)"
trap 'rm -rf "$ICONDIR"' EXIT
ICONSET="$ICONDIR/AppIcon.iconset"
mkdir -p "$ICONSET"
for s in 16 32 64 128 256 512; do
    sips -z "$s" "$s" frontend/public/vicinusAI.png \
        --out "$ICONSET/icon_${s}x${s}.png" > /dev/null
    d=$((s * 2))
    sips -z "$d" "$d" frontend/public/vicinusAI.png \
        --out "$ICONSET/icon_${s}x${s}@2x.png" > /dev/null
done
iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/VicinusAI.icns"

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
    <key>CFBundleIconFile</key>          <string>VicinusAI</string>
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
