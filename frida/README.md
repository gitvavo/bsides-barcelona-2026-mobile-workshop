# Mockapp Home Lab — Frida pinning bypass

This script targets **Mockapp Home Lab**, an intentionally vulnerable local Android app. It hooks the application-specific `WorkshopPinVerifier.isPinned(X509Certificate)`, rather than globally disabling TLS trust checks.

## Requirements

- Root-capable AOSP Android Emulator (API 34 recommended).
- Home Lab APK `mockapp-home-lab-v0.5.0-debug.apk`.
- Local Docker backend (HTTP port 8000, HTTPS port 9443).
- Burp listening on `127.0.0.1:8088`, configured with **Redirect to host = 127.0.0.1**.
- Supplied custom Burp certificate loaded in the listener, with the workshop CA installed as an Android user CA.
- **Visible Android Wi-Fi proxy** set to `10.0.2.2:8088`; do not use the separate Android Emulator Extended Controls upstream proxy.
- Desktop Frida version **17.24.3** and the supplied **`frida-server-17.24.3-android-x86_64.zip`** archive in this directory. This binary targets **Android x86_64**; use another official Frida asset if your emulator reports a different ABI.

## Start Frida Server

Extract `frida-server-17.24.3-android-x86_64.zip` into this directory. On Windows, use **Extract All** in File Explorer; on Linux/macOS, run `unzip frida-server-17.24.3-android-x86_64.zip`. The ZIP contains a ready-named `frida-server` executable. Check your desktop version with `frida --version` (the workshop-tested version is 17.24.3).

Run these commands from inside this `frida/` directory:

```sh
adb shell getprop ro.product.cpu.abi
adb root
adb shell id
adb push frida-server /data/local/tmp/frida-server
adb shell chmod 755 /data/local/tmp/frida-server
adb shell "/data/local/tmp/frida-server >/dev/null 2>&1 &"
frida-ps -U
```

If `adb root` is refused, switch to a root-capable AOSP emulator image.

## Pinning test

1. In Mockapp select **⚗ Lab Testing → HTTPS + Pinning → Save**.
2. Force-stop and relaunch the app to apply the selection.
3. With Burp configured, confirm that a request fails the custom public-key pin.
4. From the directory containing the script, run:

```sh
adb shell am force-stop com.mockapp.loyalty
frida -U -l ./bypass-mockapp-pinning.js -f com.mockapp.loyalty
```

5. Make a network request and check that Burp now sees HTTPS traffic.
6. Restart the app without Frida to verify pinning is enforced again.

The Frida hook only bypasses Mockapp's deliberate SPKI pin decision. It does not remove Android's TLS chain trust or hostname validation. If you see a certificate verification or hostname mismatch, check the workshop CA and Burp's custom server certificate first.

Frida Server must be restarted after an emulator reboot. Disable the proxy afterwards through the emulator's normal **Wi-Fi network settings → Proxy → None**.

For complete Docker, Burp import and emulator preparation instructions, see [the Home Lab guide](../docs/HOME-LAB.md) in this repository.
