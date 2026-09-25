---
name: ios-native-app
description: Author and prepare native iOS apps from Windows with a strict macOS build handoff contract
---

# Native iOS Development (from Windows)

## Hard truth
Xcode, iOS Simulator, and App Store signing ONLY run on macOS. This PC cannot build or run iOS binaries. Your job: produce a complete, buildable-on-mac source tree + an exact build contract. NEVER claim an iOS build/test happened on this PC.

## What you CAN do fully
- Write complete SwiftUI apps: Views, models, services, tests (XCTest).
- Define the project with **XcodeGen** (`project.yml`) or **Swift Package Manager** layout - both open instantly on a mac without checked-in .xcodeproj merge pain.
- Business logic tests that compile anywhere Swift exists; UI runtime verification is mac-only.

## Source layout (XcodeGen contract)
```
project.yml            # targets, signing placeholder, deployment target iOS 17+
Sources/               # SwiftUI app code
Tests/                 # XCTest unit tests
IOS_BUILD_NOTES.md     # the handoff contract
```

## IOS_BUILD_NOTES.md must contain
1. Exact mac commands: `brew install xcodegen`, `xcodegen generate`, `open *.xcodeproj`, Cmd+R.
2. Signing steps (team ID placeholder - operator fills), capabilities/entitlements needed.
3. Every Info.plist permission key + reason string used.
4. Known mac-only verification steps (simulator matrix, device run).

## Local data law
SwiftData (or SQLite via GRDB) - local only. No CloudKit/iCloud unless the task explicitly demands it.

## Done criteria (Windows side)
All sources + project.yml + tests + notes complete; Swift files syntax-reviewed; handoff contract written. State clearly: "iOS build pending macOS".
