---
name: android-native-app
description: Native Android app development on Windows with Kotlin, Gradle, and the attached S26 device
---

# Native Android Development (Kotlin, Windows)

## Environment truths (this PC)
- Physical device: S26 Ultra, USB ADB id `R3GL605J0AH`. ALWAYS `adb devices` before gradle device tasks.
- Build system: Gradle wrapper (`gradlew.bat`). JDK: use the one Android Studio/gradle config expects (`java -version` to confirm).
- Emulators are optional; prefer the physical device (faster, real perf).

## Stack defaults
- Kotlin + Jetpack Compose; Material 3; single-activity + Navigation Compose.
- DI: Hilt. Async: coroutines + Flow. Serialization: kotlinx.serialization.
- Local DB: Room (SQLite) - migrations in `Migration.kt`, NEVER `fallbackToDestructiveMigration()` in shipped code (data loss) unless the task is a throwaway prototype.

## Loop
```
./gradlew.bat assembleDebug
./gradlew.bat lint
./gradlew.bat testDebugUnitTest
adb -s R3GL605J0AH install -r app/build/outputs/apk/debug/app-debug.apk
adb -s R3GL605J0AH logcat -d -s <TAG>           # targeted logs
```

## Device evidence
- Screenshot: `adb -s R3GL605J0AH exec-out screencap -p > evidence.png`
- UI dump: `adb -s R3GL605J0AH exec-out uiautomator dump /dev/tty`

## Law
- minSdk 26+, targetSdk latest stable. No cloud services; Room/files only for persistence.
- Secrets: `local.properties` (gitignored) or env at build; never in source.
