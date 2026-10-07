# Prove-am iOS release

The Capacitor wrapper is prepared with:

- App name: Prove-am
- Bundle ID: com.proveam.app
- Production URL: https://prove-am.onrender.com
- Version: 1.0.0
- iOS simulator build verified in GitHub Actions

## Before TestFlight

An Apple Developer Program membership is required for signing and App Store distribution.

Once Apple credentials are available:

1. Create the App Store Connect app using bundle ID com.proveam.app.
2. Create/register the matching Apple App ID.
3. Configure distribution signing and provisioning.
4. Build the iOS archive for device distribution.
5. Upload the signed build to App Store Connect.
6. Enable TestFlight testing.

The production Prove-am web app remains separate from this mobile wrapper.
