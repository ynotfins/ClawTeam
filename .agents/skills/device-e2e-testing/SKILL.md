---
name: device-e2e-testing
description: E2E testing with the attached S26 Android device (adb) and Playwright MCP browser for web
---

# E2E Testing: Real Device + Browser (this PC's assets)

## Assets on this PC
- Android: S26 Ultra attached via USB, ADB id `R3GL605J0AH` (Samsung SM_S948U).
- Browser: Playwright MCP server wired into agent configs (mcp tools) for web E2E.
- Phone is OPERATOR-HELD: before ANY scripted input on the phone, run
  `adb -s R3GL605J0AH shell dumpsys window | grep mCurrentFocus` and abort UI automation if a personal app (Messages, phone dialer, camera) is focused. Installing, launching YOUR test app, logcat, screenshots are always safe.

## Android device loop
```
adb devices                                   # must show R3GL605J0AH
adb -s R3GL605J0AH install -r <apk>
adb -s R3GL605J0AH shell monkey -p <pkg> -c android.intent.category.LAUNCHER 1
adb -s R3GL605J0AH logcat -d | grep -iE "FATAL|<app tag>"
adb -s R3GL605J0AH exec-out screencap -p > e2e-01-launch.png
adb -s R3GL605J0AH exec-out uiautomator dump /dev/tty   # assert visible text
```
- Evidence = screenshots at each step + logcat clean of FATAL/ANR for the app's package.

## Web E2E (Playwright MCP)
- Drive real navigation: open the app URL, click the primary flow, assert result text/screenshots.
- Always run against the PRODUCTION build server (pnpm build && pnpm start), not just dev mode, for the final pass.

## Pass criteria
1. The full user journey completes on the real device/browser.
2. Evidence artifacts captured (screenshots/logs) and their paths cited in the completion report.
3. No FATAL exceptions, no unhandled promise rejections in logs during the run.
4. Network-failure path tested once (airplane-mode / server-stopped) for offline-first apps.
