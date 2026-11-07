/* Workshop-only runtime instrumentation of Mockapp's environment checks. */
Java.perform(function () {
    const Checks = Java.use('com.mockapp.loyalty.DeviceChecks');
    Checks.isEmulator.implementation = function () {
        console.log('[Mockapp] Replaced emulator detection result');
        return false;
    };
    Checks.isRooted.implementation = function () {
        console.log('[Mockapp] Replaced root detection result');
        return false;
    };
    console.log('[Mockapp] Device-check hooks installed');
});
