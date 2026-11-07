# BSides Barcelona 2026 — Mobile Security Workshop

**Android + iOS security concepts; Android hands-on exercises.**

This repository is the self-contained, local-only **Mockapp Home Lab** for BSides Barcelona 2026. Mockapp is intentionally vulnerable: do not expose the Docker API or Lab Settings outside your computer and do not use the included certificates for production.

## Start the workshop site

Install Docker and Docker Compose, then from the repository root:

```sh
docker compose up -d --build
```

Open **[http://localhost:8080](http://localhost:8080)**.

The browser portal provides:

| Page | Purpose |
|---|---|
| [Exercises](http://localhost:8080/) | Seven hands-on challenges, four hint levels, local progress |
| [Setup](http://localhost:8080/setup) | Windows/Linux/macOS emulator creation, Burp, CA and Frida walkthrough |
| [Downloads](http://localhost:8080/downloads) | Workshop assets, including Frida and the attendee bundle |
| [Solutions](http://localhost:8080/solutions) | All seven solutions, available from the start |
| [Lab Settings](http://localhost:8080/#settings) | Backend status, reset, transport mode guidance |

**The Markdown instructions remain available as an alternative:** [docs/HOME-LAB.md](docs/HOME-LAB.md) and [frida/README.md](frida/README.md).

The local HTTP API is bound to `127.0.0.1:8000`, HTTPS API to `127.0.0.1:9443`, and the portal to `127.0.0.1:8080`. The Android emulator uses the host alias `10.0.2.2`. The bundled Android debug APK is designed to trust the local test server and separately demonstrate optional pinning.

## Repository layout

```text
.
├── Dockerfile
├── docker-compose.yml
├── backend/               # FastAPI API, lab reset and HTML portal
│   └── portal/             # HTML pages: setup, exercises, solutions, downloads
├── docs/                   # Markdown documentation
├── frida/                  # Frida Server ZIP and scripts
├── app/                    # Release APK (debug)
├── burp/                   # Imported project settings and dedicated lab CA/.p12
├── slides/                 # Workshop PowerPoint
└── setup/                  # Short emulator proxy configuration GIF
```

All seven exercises and their solutions are served locally by Docker. The **readable** sources and guidance remain in this repository for users who don't want the browser portal.

## Release assets

All workshop release assets are included: the Android debug APK, revised PowerPoint, Burp settings and dedicated test certificates, the Wi-Fi proxy GIF, plus Frida Server ZIP and bypass scripts. The [asset checksums](SHA256SUMS.txt) can be verified using `sha256sum -c SHA256SUMS.txt` on Linux/macOS. Start Docker with `docker compose up -d --build` to make the assets available from the local Downloads page.

For attendees, the standard Burp listener is `127.0.0.1:8088` with the destination redirected to `127.0.0.1`. Configure the emulator proxy through **Android Wi-Fi Settings** (not ADB's global proxy setting or Emulator Extended Controls).

## Safety and reproducibility

- Lab certificates and private keys are deliberately shared **test-only** assets; they are not valid for production services.
- The app is a **debug** build to allow the lab's ADB and file-inspection exercises.
- Reset in Lab Settings destroys the local DB state and re-seeds demo accounts.
- Do not deploy this vulnerable API to a public or shared network.
- For a clean reset of Docker volumes: `docker compose down -v` removes all saved lab data.

## Attribution

Prepared for the BSides Barcelona 2026 Mobile Pentesting Workshop. Android exercises use Mockapp; iOS topics are presented conceptually in the slides.
