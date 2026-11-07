# Mockapp Home Lab

A deliberately vulnerable **local-only Android security training lab**, for Android API 34 AOSP emulator, Burp Community, Frida and a Docker backend. Do not deploy on an internet-facing server.

## Quick start

1. [Create an AOSP Android 14 emulator](#create-the-android-14-emulator-windows-linux-and-macos) using the OS-specific steps below. Install Docker Desktop or Docker Engine, Burp Suite, JADX-GUI and Frida tools.
2. Start the backend in this repository: `docker compose up -d --build`.
3. Open **http://localhost:8080** on your host to see exercises, hints and Lab Settings.
4. Install **mockapp-home-lab-v0.5.0-debug.apk** on your emulator, for example: `adb install -r mockapp-home-lab-v0.5.0-debug.apk`.
5. Default backend address from the emulator: `https://10.0.2.2:9443`. HTTP mode uses port 8000. The emulator-only address `10.0.2.2` is not Windows/Linux/macOS localhost.
6. Inside Mockapp, tap **⚗ Lab Testing** to switch between HTTP, HTTPS and HTTPS + Pinning. After each change, force-stop Mockapp and relaunch it.

```sh
adb shell am force-stop com.mockapp.loyalty
adb shell monkey -p com.mockapp.loyalty -c android.intent.category.LAUNCHER 1
```

## Create the Android 14 emulator (Windows, Linux and macOS)

**Target:** AOSP Android 14 / API 34. Use **x86_64** on Windows, x86_64 Linux or Intel macOS. Apple Silicon uses **ARM64** and needs an ARM64 Frida Server instead of the bundled x86_64 ZIP. **Do not select a Google Play system image**: the Frida lab requires `adb root` and Play images generally prevent it.

### Windows (PowerShell)

1. Enable **Intel VT-x / AMD-V** in BIOS/UEFI. Enable **Windows Hypervisor Platform** as necessary and restart Windows.
2. Install [Android Studio](https://developer.android.com/studio) and use its SDK Manager to install **Android 14 (API 34), Android Emulator, Android SDK Platform-Tools, and the API 34 AOSP x86_64 system image**. The Android Studio installer includes a JDK for Android Studio itself; standalone SDK tools may need a separately configured JDK 17+.
3. Alternatively, install the official Android CLI and SDK basics, then obtain the AOSP system image using Android Studio's SDK Manager or the SDK Command-line Tools.

```powershell
winget install --id Google.AndroidCLI
# Open a new PowerShell window first
android sdk install platform-tools emulator platforms/android-34
android sdk list --all
```

4. In **Android Studio → Tools → Device Manager → Create Virtual Device**, select a phone; select **Android 14 / API 34, AOSP, x86_64**. Do not choose a Play Store image.
5. If `adb` or `emulator` isn't found, restart the shell and ensure the installed SDK's `platform-tools` and `emulator` folders are on PATH.

### Linux (Bash)

1. Enable VT-x/AMD-V in BIOS/UEFI, check `/dev/kvm`, and ensure your user has permission to use KVM. If you add yourself to the `kvm` group, **log out and back in** before proceeding.
2. Install OpenJDK 17+ (if using standalone SDK tools), and [Android Studio](https://developer.android.com/studio).
3. In Android Studio's SDK Manager, install **API 34**, SDK Platform-Tools, Android Emulator and the **API 34 AOSP x86_64 system image**.
4. In **Tools → Device Manager**, create an Android 14 AOSP x86_64 virtual device.

```bash
java -version
ls -l /dev/kvm
# Restart the terminal after changing PATH or JAVA_HOME.
```

### macOS (Terminal)

1. Install [Android Studio](https://developer.android.com/studio), SDK Platform 34, Platform-Tools, Android Emulator and an AOSP API 34 image.
2. On **Intel Macs**, select the x86_64 image. On **Apple Silicon**, select **ARM64** and obtain **Frida Server 17.24.3 for Android ARM64** separately; the bundled x86_64 ZIP is not compatible.
3. Android Studio includes a JDK for IDE tooling. For standalone SDK command-line tools, install/configure JDK 17+ as needed. Open a fresh terminal after changing PATH or JAVA_HOME.

```bash
uname -m
java -version
```

### Configure and start the AVD

Recommended AVD name: `Mockapp_API_34`. Suggested screen: **1080 × 1920**, density **480 dpi**, data partition **10 GB**, hardware keyboard input **on**. Set these in AVD Advanced Settings or its `config.ini`. The exact display configuration is not security-critical for this lab.

Start the AVD using Android Studio Device Manager. An equivalent CLI workflow, if the Android SDK Command-line Tools are installed and their `bin` directory is on PATH, is:

```bash
sdkmanager "system-images;android-34;default;x86_64"
avdmanager create avd -n Mockapp_API_34 -k "system-images;android-34;default;x86_64"
emulator @Mockapp_API_34
```

The example above is **x86_64 only**; ARM64 hosts need a compatible ARM64 image/package instead. To check the emulator after it boots:

```bash
adb devices
adb shell getprop ro.build.version.sdk
adb shell getprop ro.product.cpu.abi
adb root
adb shell id
```

You should see API `34`, the correct ABI, and `uid=0(root)` after `adb root`. The emulator serial is often `emulator-5554` but may differ. If `adb root` fails with a production-build error, create an AOSP non-Play AVD; if the device shows `unauthorized`, accept the device prompt. Continue with Docker and the APK only after you have verified ADB.

## Emulator preparation: Burp

**Files needed from the workshop package:** the included `burp/mockapp-burp-project-settings.json`, a custom lab `.p12` server certificate, the matching public `lab-ca.crt`, and the password supplied with the workshop files.

1. In Burp, **import the project settings JSON**. Check **Settings → Tools → Proxy → Proxy listeners**.
2. Verify the listener is on `127.0.0.1:8088` with **Redirect to host = 127.0.0.1** and no forced destination port.
3. Edit listener → **Certificate** → **Use a custom certificate**. **Browse to the provided `.p12` at the location you saved it** and enter the workshop password. An exported Burp JSON may contain no usable path on a different computer; this step is mandatory.
4. Copy the public CA to the emulator:

```sh
adb push lab-ca.crt /sdcard/Download/lab-ca.crt
```

5. On Android, open **Settings → Security & privacy → More security & privacy → Encryption & credentials → Install a certificate → CA certificate**. Select `lab-ca.crt` in Downloads. Actual menu wording may vary.
6. Configure the **visible Android Wi-Fi proxy** (not the separate Android Emulator Extended Controls upstream proxy): **Settings → Network & internet → Internet → AndroidWifi → Edit → Advanced → Proxy → Manual**; hostname `10.0.2.2`, port `8088`. Save. To restore normal networking, set **Proxy → None** using the same interface.
7. Verify HTTP mode intercepts normally. In HTTPS mode, verify Burp decrypts HTTPS. In HTTPS + Pinning mode, expect a rejection until the Frida hook runs.

The public CA file is installed in Android; **do not** install the `.p12` or any private key into Android. The `.p12` is selected only in Burp.

## Emulator preparation: Frida

Use a root-capable emulator and a `frida-server` build that matches the Android emulator ABI and your desktop Frida version.

```sh
adb shell getprop ro.product.cpu.abi
adb root
adb shell id
adb push frida-server /data/local/tmp/frida-server
adb shell chmod 755 /data/local/tmp/frida-server
adb shell "/data/local/tmp/frida-server >/dev/null 2>&1 &"
frida-ps -U
```

If `adb root` is refused, use a root-capable AOSP emulator image rather than a locked Google Play image. Restart Frida Server after rebooting the emulator.

From a directory containing `bypass-mockapp-pinning.js`, in HTTPS + Pinning mode:

```sh
frida -U -l ./bypass-mockapp-pinning.js -f com.mockapp.loyalty
```

Frida bypasses Mockapp's test-only pin decision, not Android's general certificate trust or hostname verification.

## Exercises, hints and reset

The local portal at **http://localhost:8080** offers seven exercises, four hint levels and lab reset. Level 3 includes step-by-step instructions. Demo accounts include `alice / coffee1042` and `bob / coffee1043`. Reset destroys local accounts, sessions, transfers and redemptions and restores seeded users. Any progress checkbox state is local to the browser.

## Troubleshooting

- **Burp times out connecting to 10.0.2.2:** Its request-handling redirect to `127.0.0.1` is missing. Only the Android emulator can resolve its special `10.0.2.2` alias to the host.
- **HTTPS hostname-verification error:** Verify Burp uses the supplied custom certificate with an IP-type SAN for `10.0.2.2`.
- **Unknown certificate authority:** Install the supplied `lab-ca.crt` into Android's user CA store.
- **No intercepted HTTPS:** Verify Android **Wi-Fi Proxy** is Manual and the Emulator Extended Controls upstream-proxy is not configured.
- **Frida says jailed device/Gadget required:** Start the matching `frida-server` on the root-capable emulator.
- **App mode does not switch:** Force-stop and relaunch it.

## Local security

Docker binds HTTP, HTTPS and Lab Settings ports to the host loopback interface. The HTTPS key and the Burp interception key are disposable, public workshop-only credentials. Never use them for real services.

## Checks

```sh
docker compose ps
curl http://127.0.0.1:8000/api/v1/health
curl -k https://127.0.0.1:9443/api/v1/health
```
