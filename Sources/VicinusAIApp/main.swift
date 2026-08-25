import AppKit
import CoreText
import WebKit

private func registerFont(_ name: String) {
    guard let dir = Bundle.main.resourcePath,
          FileManager.default.fileExists(atPath: "\(dir)/\(name).ttf") else { return }
    let url = URL(fileURLWithPath: "\(dir)/\(name).ttf")
    var err: Unmanaged<CFError>?
    CTFontManagerRegisterFontsForURL(url as CFURL, .process, &err)
    _ = err // already registered is fine
}

private func uiFont(_ psName: String, _ size: CGFloat) -> NSFont {
    NSFont(name: psName, size: size) ?? .systemFont(ofSize: size, weight: .regular)
}

final class AppDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate {
    private var window: NSWindow!
    private var container: NSView!
    private var launcherStack: NSStackView!
    private var titleLabel: NSTextField!
    private var statusLabel: NSTextField!
    private var startButton: NSButton!
    private var webView: WKWebView?
    private var serverProcess: Process?
    private var pendingOutput = Data()
    private var outputTail: [String] = []
    private var isReady = false
    private var signalSources: [DispatchSourceSignal] = []
    private let flaskURL = URL(string: "http://127.0.0.1:5001")!

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        NSApp.appearance = NSAppearance(named: .aqua)
        registerFont("StackSansNotch-Regular")
        registerFont("StackSansNotch-Bold")
        buildUI()
        installSignalHandlers()
        NSApp.activate(ignoringOtherApps: true)
        if locateCLI() == nil {
            promptRemoveSelf()
            return
        }
        if ProcessInfo.processInfo.environment["VICINUS_AI_GUI_AUTOSTART"] == "1" {
            DispatchQueue.main.async { self.startServers() }
        }
    }

    private func promptRemoveSelf() {
        let alert = NSAlert()
        alert.messageText = "VicinusAI backend not found"
        alert.informativeText =
            "vicinus-ai-cli was not found. Has the Homebrew formula been uninstalled?\n\n" +
            "Would you like to remove this application from /Applications?"
        alert.alertStyle = .warning
        alert.addButton(withTitle: "Remove app")
        alert.addButton(withTitle: "Cancel")
        if alert.runModal() == .alertFirstButtonReturn {
            let appPath = Bundle.main.bundlePath
            NSWorkspace.shared.activateFileViewerSelecting([URL(fileURLWithPath: appPath)])
            NSApp.terminate(nil)
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                try? FileManager.default.removeItem(atPath: appPath)
            }
        }
        NSApp.terminate(nil)
    }

    private func installSignalHandlers() {
        for sig in [SIGTERM, SIGINT] {
            signal(sig, SIG_IGN)
            let source = DispatchSource.makeSignalSource(signal: sig, queue: .main)
            source.setEventHandler { [weak self] in
                print("[gui] SIGNAL \(sig) received -> stopping servers")
                self?.stopServers()
                exit(0)
            }
            source.resume()
            signalSources.append(source)
        }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        true
    }

    func applicationWillTerminate(_ notification: Notification) {
        print("[gui] applicationWillTerminate")
        stopServers()
    }

    // MARK: - UI

    private func buildUI() {
        window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 1150, height: 780),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered, defer: false)
        window.title = "VicinusAI"
        window.center()

        container = NSView(frame: window.contentLayoutRect)
        container.wantsLayer = true
        container.layer?.backgroundColor = NSColor.white.cgColor
        window.contentView = container

        titleLabel = NSTextField(labelWithString: "VicinusAI")
        titleLabel.font = uiFont("StackSansNotch-Bold", 46)
        titleLabel.textColor = NSColor.black

        statusLabel = NSTextField(wrappingLabelWithString: "Servers are not running.")
        statusLabel.font = uiFont("StackSansNotch-Regular", 18)
        statusLabel.textColor = NSColor.black
        statusLabel.maximumNumberOfLines = 6
        statusLabel.preferredMaxLayoutWidth = 620
        statusLabel.alignment = .center

        startButton = NSButton(title: "Start servers", target: self, action: #selector(startServers))
        startButton.bezelStyle = .rounded
        startButton.controlSize = .large
        startButton.font = uiFont("StackSansNotch-Regular", 22)
        startButton.hasDestructiveAction = false
        startButton.keyEquivalent = "\r"

        launcherStack = NSStackView(views: [titleLabel, statusLabel, startButton])
        launcherStack.orientation = .vertical
        launcherStack.alignment = .centerX
        launcherStack.spacing = 22
        launcherStack.translatesAutoresizingMaskIntoConstraints = false
        container.addSubview(launcherStack)

        NSLayoutConstraint.activate([
            launcherStack.centerXAnchor.constraint(equalTo: container.centerXAnchor),
            launcherStack.centerYAnchor.constraint(equalTo: container.centerYAnchor),
            statusLabel.widthAnchor.constraint(lessThanOrEqualToConstant: 640),
        ])

        window.makeKeyAndOrderFront(nil)
    }

    private func resetLauncher(status: String) {
        webView?.removeFromSuperview()
        webView = nil
        isReady = false
        serverProcess = nil
        statusLabel.stringValue = status
        statusLabel.textColor = NSColor.black
        startButton.isHidden = false
        startButton.isEnabled = true
        launcherStack.isHidden = false
    }

    // MARK: - Process management

    @objc private func startServers() {
        guard let cli = locateCLI() else {
            promptRemoveSelf()
            return
        }
        startButton.isEnabled = false
        statusLabel.stringValue = "Starting servers… (first launch may download the model)"
        outputTail.removeAll()
        pendingOutput.removeAll()

        let proc = Process()
        proc.executableURL = cli
        proc.arguments = []
        var env = ProcessInfo.processInfo.environment
        env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:" + (env["PATH"] ?? "")
        proc.environment = env
        let pipe = Pipe()
        proc.standardOutput = pipe
        proc.standardError = pipe
        proc.terminationHandler = { [weak self] process in
            guard let self else { return }
            DispatchQueue.main.async {
                guard self.serverProcess === process else { return }
                let tail = self.outputTail.suffix(8).joined(separator: "\n")
                if process.terminationStatus == 0 || self.isReady {
                    self.resetLauncher(status: "Servers stopped.")
                } else {
                    self.resetLauncher(
                        status: "Servers exited unexpectedly (\(process.terminationStatus)).\n\(tail)")
                }
            }
        }
        pipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard let self, !data.isEmpty else { return }
            self.consume(data)
        }
        do {
            try proc.run()
        } catch {
            statusLabel.stringValue = "Failed to launch vicinus-ai-cli:\n\(error.localizedDescription)"
            startButton.isEnabled = true
            return
        }
        serverProcess = proc
    }

    private func stopServers() {
        guard let proc = serverProcess, proc.isRunning else { return }
        print("[gui] terminating orchestrator pid=\(proc.processIdentifier)")
        proc.terminate()
        let deadline = Date().addingTimeInterval(6)
        while proc.isRunning && Date() < deadline {
            Thread.sleep(forTimeInterval: 0.1)
        }
        if proc.isRunning { kill(proc.processIdentifier, SIGKILL) }
    }

    private func consume(_ data: Data) {
        pendingOutput.append(data)
        while let nl = pendingOutput.firstIndex(of: 0x0A) {
            let lineData = pendingOutput.subdata(in: pendingOutput.startIndex..<nl)
            pendingOutput.removeSubrange(pendingOutput.startIndex...nl)
            let line = String(data: lineData, encoding: .utf8) ?? ""
            DispatchQueue.main.async {
                self.handleLine(line)
            }
        }
    }

    private func handleLine(_ line: String) {
        let trimmed = line.trimmingCharacters(in: .whitespaces)
        guard !trimmed.isEmpty else { return }
        if ProcessInfo.processInfo.environment["VICINUS_AI_GUI_DEBUG"] == "1" {
            print("[gui] LINE: \(trimmed)")
        }
        outputTail.append(trimmed)
        if outputTail.count > 40 { outputTail.removeFirst(outputTail.count - 40) }
        if !isReady {
            statusLabel.stringValue = trimmed
        }
        if trimmed.contains("AI server ready") && !isReady {
            swapToWebView()
        }
    }

    // MARK: - WebView

    private func swapToWebView() {
        isReady = true
        if ProcessInfo.processInfo.environment["VICINUS_AI_GUI_DEBUG"] == "1" {
            print("[gui] WEBVIEW SWAP")
        }
        let web = WKWebView(frame: container.bounds)
        web.autoresizingMask = [.width, .height]
        web.navigationDelegate = self
        container.addSubview(web)
        webView = web
        launcherStack.isHidden = true
        web.load(URLRequest(url: flaskURL))
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        if ProcessInfo.processInfo.environment["VICINUS_AI_GUI_DEBUG"] == "1" {
            print("[gui] NAV DONE \(webView.url ?? URL(string: "about:blank")!)")
        }
    }

    func webView(
        _ webView: WKWebView,
        decidePolicyFor navigationAction: WKNavigationAction,
        decisionHandler: @escaping (WKNavigationActionPolicy) -> Void
    ) {
        guard let url = navigationAction.request.url,
              let host = url.host,
              url.port == 5001,
              host == "127.0.0.1" || host == "localhost" else {
            if let url = navigationAction.request.url,
               url.scheme == "http" || url.scheme == "https" {
                NSWorkspace.shared.open(url)
            }
            decisionHandler(.cancel)
            return
        }
        decisionHandler(.allow)
    }

    func webView(
        _ webView: WKWebView,
        createWebViewWith configuration: WKWebViewConfiguration,
        for navigationAction: WKNavigationAction,
        windowFeatures: WKWindowFeatures
    ) -> WKWebView? {
        if let url = navigationAction.request.url {
            NSWorkspace.shared.open(url)
        }
        return nil
    }

    // MARK: - CLI discovery

    private func locateCLI() -> URL? {
        let candidates = [
            "/opt/homebrew/bin/vicinus-ai-cli",
            "/usr/local/bin/vicinus-ai-cli",
        ]
        for path in candidates where FileManager.default.isExecutableFile(atPath: path) {
            return URL(fileURLWithPath: path)
        }
        let which = Process()
        which.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        which.arguments = ["which", "vicinus-ai-cli"]
        let pipe = Pipe()
        which.standardOutput = pipe
        which.standardError = FileHandle.nullDevice
        do {
            try which.run()
            which.waitUntilExit()
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            if let path = String(data: data, encoding: .utf8)?
                .trimmingCharacters(in: .whitespacesAndNewlines),
                !path.isEmpty, FileManager.default.isExecutableFile(atPath: path) {
                return URL(fileURLWithPath: path)
            }
        } catch {}
        return nil
    }
}

let app = NSApplication.shared
setbuf(stdout, nil)
let delegate = AppDelegate()
app.delegate = delegate
app.run()
