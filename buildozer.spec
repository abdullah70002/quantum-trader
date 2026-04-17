# ╔═══════════════════════════════════════════════════════════════════════╗
# ║          QUANTUM TRADER — buildozer.spec                             ║
# ║                                                                       ║
# ║  ⚠️  IMPORTANT NOTE:                                                 ║
# ║  Flet does NOT use Buildozer. Flet compiles to a Flutter APK via:    ║
# ║      flet build apk                                                   ║
# ║  This file is provided as a reference / fallback in case you ever    ║
# ║  decide to port the project to Kivy/KivyMD instead of Flet.          ║
# ║  The GitHub Actions workflow (android.yml) uses the correct           ║
# ║  "flet build apk" command automatically.                              ║
# ╚═══════════════════════════════════════════════════════════════════════╝

[app]

# ── Basic identity ──────────────────────────────────────────────────────
title        = Quantum Trader
package.name = quantumtrader
package.domain = com.quantumtrader

source.dir   = .
source.include_exts = py,png,jpg,kv,atlas,json

# ── Version ─────────────────────────────────────────────────────────────
version = 1.0.0

# ── Entry point ─────────────────────────────────────────────────────────
# NOTE: change to main.py for Kivy port; Flet ignores this field entirely
entrypoint = main.py

# ── Python requirements ─────────────────────────────────────────────────
# When porting to Kivy, replace "flet" with "kivy,kivymd"
requirements = python3==3.11.8,flet,pandas,numpy,ccxt,yfinance,requests,urllib3,certifi,charset-normalizer,idna

# ── Screen orientation ──────────────────────────────────────────────────
orientation = portrait

# ── Android permissions ─────────────────────────────────────────────────
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

# ── Android API levels ──────────────────────────────────────────────────
android.minapi = 21
android.api    = 33
android.ndk    = 25b
android.sdk    = 33

# ── Architecture (arm64-v8a covers modern Android phones) ────────────────
android.archs = arm64-v8a,armeabi-v7a

# ── Accept SDK license automatically ────────────────────────────────────
android.accept_sdk_license = True

# ── Icon & Splash ────────────────────────────────────────────────────────
# Uncomment and provide the file paths when ready:
# icon.filename      = %(source.dir)s/assets/icon.png
# presplash.filename = %(source.dir)s/assets/splash.png

# ── Build type ──────────────────────────────────────────────────────────
android.release_artifact = apk

# ── Gradle extras ───────────────────────────────────────────────────────
android.gradle_dependencies =

# ── Logcat filters (debugging) ──────────────────────────────────────────
android.logcat_filters = *:S python:D

# ── p4a bootstrap (Kivy default) ────────────────────────────────────────
# p4a.bootstrap = sdl2

[buildozer]
# Set to 1 for verbose build output
log_level = 2
warn_on_root = 1
