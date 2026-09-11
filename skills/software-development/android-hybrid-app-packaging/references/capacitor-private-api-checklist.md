# Capacitor APK + private API checklist

## Build inputs

```bash
npm install --save-exact @capacitor/core@7 @capacitor/android@7
npm install --save-dev --save-exact @capacitor/cli@7
VITE_API_BASE=http://PRIVATE_HOST:PORT npm run build && npx cap sync android
```

Use the same major for all Capacitor packages. The `&&` is intentional: it prevents stale `dist/` assets from being copied after a failed build.

## Capacitor config essentials

```ts
const config: CapacitorConfig = {
  appId: 'com.example.app',
  appName: 'Example App',
  webDir: 'dist',
  server: { androidScheme: 'https', cleartext: true },
  android: { allowMixedContent: true },
}
```

`cleartext`/`allowMixedContent` do not replace Android manifest verification.

## Exact-host Android network policy

`android/app/src/main/res/xml/network_security_config.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
  <base-config cleartextTrafficPermitted="false" />
  <domain-config cleartextTrafficPermitted="true">
    <domain includeSubdomains="false">PRIVATE_HOST</domain>
  </domain-config>
</network-security-config>
```

In `<application>`:

```xml
android:networkSecurityConfig="@xml/network_security_config"
```

Keep `<uses-permission android:name="android.permission.INTERNET" />` and avoid unrelated permissions.

## Private API verification

```bash
curl -H 'Origin: capacitor://localhost' http://PRIVATE_HOST:PORT/api/health
```

Require HTTP 200 and `Access-Control-Allow-Origin: capacitor://localhost`. Bind the service to the private/Tailscale IP, not `0.0.0.0`.

## Gradle build

```bash
export JAVA_HOME="$HOME/.local/share/jdks/temurin-21"
export PATH="$JAVA_HOME/bin:$PATH"
export ANDROID_HOME="$HOME/Android/Sdk"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
cd android
./gradlew assembleDebug --no-daemon
```

If Gradle reports an unsupported class-file major, select a supported JDK; do not change application code.

## Artifact checks

```bash
apksigner verify --verbose --print-certs app-debug.apk
aapt dump badging app-debug.apk
sha256sum app-debug.apk
stat --printf='size_bytes=%s\n' app-debug.apk
adb devices
```

Additionally inspect the APK ZIP for current `assets/public/` files and the intended API base. Inspect the compiled manifest for `networkSecurityConfig` and `INTERNET`.

Debug APKs are suitable for direct testing but are not Play Store release artifacts. If no device is listed, disclose that installation/runtime was not physically tested.
