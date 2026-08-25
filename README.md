# Hi! Welcome to Vicinus AI. 
<img width="1619" height="984" alt="Screenshot 2026-08-24 at 17 54 24" src="https://github.com/user-attachments/assets/e5527577-8714-4c1e-9958-3ccfe97389f1" />


## How Do I Install It?
* please check limitations before continuing.

You can run vicinus AI by just running one command!
```bash
brew install mathobsession/tap/vicinus-ai
```
once installed, you can update it using:

```bash
brew reinstall vicinus-ai
```

to run the app use:

```bash
vicinus-ai
```

On first launch it copies itself to `/Applications/VicinusAI.app` so it lives
there permanently — double-click it from Finder anytime afterwards, or keep
running `vicinus-ai` to stay up to date. The window shows a **Start servers**
button; once the stack is up, the console UI renders inside the window via
WebKit — locked to `127.0.0.1:5001`, external links open in your default
browser. Quitting the window stops all servers.

### CLI mode

```bash
vicinus-ai-cli
```

Runs the same stack without the native window — use this in scripts or
terminal-only workflows.

### Dev mode

```bash
vicinus-ai-cli --dev
```

In dev mode the web backend owns the inference server, which unlocks
**Reload model** and **Save & reload runtime flags** buttons in the settings
panel (toggle Dev mode in the sidebar). Reloading restarts
TurboFieldfareServer with the selected runtime flags (context window,
expert-cache slots, prefill, rdadvise). Sampling parameters — temperature,
top-k, top-p, seed — always apply per message, no reload needed.

## Documentation
Vicinus AI is a homebrew tap of the repository [turbo-fieldfare](https://github.com/drumih/turbo-fieldfare). It is made to simplify the use of the repository's built in server and wrap it around a calming, good looking UI.

Though it is still in beta 0.1.1 the product is relatively stable. 
We have a scheduled build release timeline of about a new update every two days in the first two weeks and then eventually shift to a monthly release.

A new repository for **Vicinus BETA** will be created by the end of August 2026 for the latest updates.

To learn more about the architecture check [turbo-fieldfare](https://github.com/drumih/turbo-fieldfare).

## Limitations
**This repository supports only Apple Silicon MacBooks and installing it on intel based Macs might cause issues.**
