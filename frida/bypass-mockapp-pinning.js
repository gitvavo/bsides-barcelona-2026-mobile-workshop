/*
 * Mockapp workshop: bypass ONLY the additional SPKI pin check.
 * Android's usual certificate trust and hostname verification stay enabled.
 * Run against the intentionally vulnerable com.mockapp.loyalty debug APK.
 */
Java.perform(function () {
    const Verifier = Java.use('com.mockapp.loyalty.WorkshopPinVerifier');
    const check = Verifier.isPinned.overload('java.security.cert.X509Certificate');
    check.implementation = function (cert) {
        let subject = '<unavailable>';
        try { subject = cert.getSubjectX500Principal().getName().toString(); } catch (_) {}
        console.log('[Mockapp] Suppressed SPKI pin rejection for: ' + subject);
        return true;
    };
    console.log('[Mockapp] Pinning bypass installed. Normal Android TLS validation remains enabled.');
});
