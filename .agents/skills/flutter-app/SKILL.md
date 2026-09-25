---
name: flutter-app
description: Build full-stack Flutter apps (Android/iOS/web/desktop) on Windows with local databases
---

# Flutter App Development (Windows-native)

## Environment truths (this PC)
- Flutter toolchain runs on Windows natively. NO Docker anywhere.
- Physical test device: Samsung S26 Ultra via USB ADB (`R3GL605J0AH`) - check `adb devices` first.
- iOS SIMULATOR/build is impossible on Windows - see the ios-native-app skill for the handoff contract.

## Project bootstrap
```
flutter create --org com.tonyapps --platforms android,ios,web,windows <app_name>
```
- Use `flutter pub add` for deps; never edit pubspec lockfiles by hand.
- State: `flutter_riverpod` (v2, codegen off for speed unless the task needs it).
- Routing: `go_router`. Serialization: `json_serializable` + `build_runner`.

## Local database (ALWAYS local - never cloud)
- Default: `drift` (SQLite) - see the local-database skill for schema/migration law.
- Simple key-value: `shared_preferences`. Structured files: `isar` only if drift is rejected.

## Build / run / test loop
```
flutter pub get
flutter analyze                      # must be clean before done
flutter test                         # unit+widget; must pass
flutter run -d R3GL605J0AH           # on-device debug (device attached via USB)
flutter build apk --release          # Android artifact
flutter build web                    # web artifact (serve with any static server)
```
- Logs from device: `adb -s R3GL605J0AH logcat -d | grep flutter`.
- Screenshots for evidence: `adb -s R3GL605J0AH exec-out screencap -p > shot.png`.

## Done criteria
- `flutter analyze` clean, `flutter test` green, app runs on the S26 or web build serves.
- No hardcoded API keys; secrets via `--dart-define` + env at build time.
