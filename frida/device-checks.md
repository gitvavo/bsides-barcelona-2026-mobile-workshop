# Environment-detection bypass demo

Use the rooted `userdebug` Mockapp emulator and the Frida tools from the earlier pinning exercise.

1. Log into Mockapp and launch its deliberately exported diagnostics activity:

```bash
adb shell am start -n com.mockapp.loyalty/.DiagnosticsActivity
```

2. Note the displayed root/emulator detection results. Also note that the activity displays the user's bearer token, a separate export/misconfiguration weakness.
3. Close the diagnostics screen and force-stop Mockapp:

```bash
adb shell am force-stop com.mockapp.loyalty
frida -U -f com.mockapp.loyalty -l frida/bypass-device-checks.js
```

4. With Frida attached, launch diagnostics again using the ADB command above.
5. The Frida overrides return `false` from both `DeviceChecks.isEmulator()` and `DeviceChecks.isRooted()`. The diagnostic screen now reports no detection. The detector has **never blocked application execution**.

The checks are deliberately simplistic and the demonstration intentionally targets one app's own methods. Do not interpret a `false` result as meaning a real device is safe.
