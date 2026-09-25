---
name: react-native-app
description: Build React Native / Expo apps for Android + iOS on Windows with local data layers
---

# React Native App Development (Windows-native)

## Environment truths (this PC)
- Node + npm/pnpm available. Expo CLI via `npx expo`. NO Docker, no WSL required.
- Physical device: S26 Ultra (`R3GL605J0AH`). `npx expo start` then scan dev-client QR or `adb reverse tcp:8081 tcp:8081`.
- iOS builds require macOS - ship a build contract (below), never fake completion.

## Stack defaults
- Expo SDK latest stable + expo-router (file routing) + TypeScript.
- State: `zustand`. Server state: `@tanstack/react-query`.
- Local DB: `expo-sqlite` (SQLite) with migrations in `db/migrations/` - see local-database skill.
- Offline-first: queue mutations locally, sync when a server exists; never block UI on network.

## Loop
```
npx expo start                       # metro; press a for Android once device visible
npx tsc --noEmit                     # types must pass
npx expo lint
npx jest --passWithNoTests
adb -s R3GL605J0AH reverse tcp:8081 tcp:8081   # if device can't reach metro
```
- Android release artifact: `eas build --profile preview --platform android` OR local `cd android && ./gradlew assembleRelease` if bare.

## iOS handoff contract (Windows reality)
Deliver: complete TS source + `app.json` + iOS-specific notes (permissions, Info.plist keys, native modules) in `IOS_BUILD_NOTES.md`. State explicitly that the iOS build must run on macOS. Never claim "built for iOS" from this PC.

## Done criteria
Type-check clean, lint clean, app loads on the S26 device, local DB migrations run, offline path works.
