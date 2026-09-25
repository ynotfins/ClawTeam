---
name: local-database
description: Local-first database law and patterns (SQLite family, PGlite, loopback Postgres) for every app type
---

# Local Database Law (ALL apps on this stack)

## Principle
ALL persistence is LOCAL on this PC: SQLite-family files, PGlite/in-process, or the loopback Postgres instances. NEVER wire cloud DBs, Firebase, Supabase, Atlas, or any hosted store. Never introduce mem0/OpenMemory or Obsidian vaults.

## Pick by app type
| App | Default | Notes |
|---|---|---|
| Flutter | drift (SQLite) | typed queries, migrations in code |
| React Native / Expo | expo-sqlite | migration runner in db/migrations/ |
| Android native | Room | versioned Migration objects |
| iOS native | SwiftData or GRDB | local files only |
| Web SPA | PGlite (in-browser PG) | or IndexedDB for simple docs |
| Web full-stack / Node | better-sqlite3 | WAL mode on |
| Python backend | sqlite3 stdlib or loopback PG | |
| Server-grade / multi-user | AgentCore PG 127.0.0.1:55433 | permission-gated; never expose beyond loopback |

## Migration law (applies to ALL)
1. Schema changes ALWAYS ship as migrations (versioned, ordered, forward-only).
2. Never destructive-by-default: no DROP TABLE / fallbackToDestructiveMigration in shipped code.
3. Seed data lives in migrations or a versioned seed script - never ad-hoc inserts.
4. Test migrations up AND from previous version before claiming done.

## Patterns
- Enable WAL on SQLite for concurrent reads (`PRAGMA journal_mode=WAL`).
- One writer at a time; queue writes through a repository layer.
- Backups = file copy (SQLite) with app stopped or after `VACUUM INTO`.
- Connection strings from env at runtime; never committed.

## Done criteria
Migrations run clean from zero AND from prior version; data survives app restart; no network calls in the data layer (assert it).
