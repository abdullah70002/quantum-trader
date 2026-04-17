# ⚡ Quantum Trader — Android APK

> **Flet-powered** trading platform | Refactored from Streamlit  
> TradingView-quality charts · Python indicator engine · GitHub Actions CI

---

## 📁 Repository Structure

```
quantum-trader/
├── main.py                          ← Flet application (entry point)
├── custom_indicators.py             ← Indicator templates (unchanged)
├── requirements.txt                 ← Python packages bundled into APK
├── buildozer.spec                   ← Reference config (Kivy fallback)
└── .github/
    └── workflows/
        └── android.yml              ← GitHub Actions — builds the APK
```

---

## 🚀 Build the APK (GitHub Actions)

1. **Create** a new GitHub repository and push all files:
   ```bash
   git init
   git remote add origin https://github.com/YOUR_USERNAME/quantum-trader.git
   git add .
   git commit -m "Initial commit — Flet Android app"
   git push -u origin main
   ```

2. **GitHub Actions** starts automatically on every push to `main`.  
   Go to **Actions → Build Quantum Trader APK → latest run**.

3. When the job finishes (≈ 15–25 min), scroll to **Artifacts** and  
   download `quantum-trader-apk.zip` → unzip → install the `.apk`.

---

## 🛠️ Build Locally (macOS / Linux)

```bash
# 1. Install Flutter 3.24
# https://docs.flutter.dev/get-started/install

# 2. Install Flet CLI
pip install "flet[all]==0.24.1"

# 3. Build
flet build apk \
  --project "Quantum Trader" \
  --org "com.quantumtrader" \
  --build-version "1.0.0" \
  --android-permissions INTERNET \
  --android-permissions READ_EXTERNAL_STORAGE \
  --android-permissions WRITE_EXTERNAL_STORAGE

# APK will be at: build/apk/quantum-trader.apk
```

---

## ⚠️ Why Not Buildozer?

| Framework | Packager       |
|-----------|----------------|
| **Kivy**  | Buildozer      |
| **Flet**  | `flet build apk` (Flutter) |

Flet is built on top of **Flutter**, not Kivy, so it has its own build  
command. The provided `buildozer.spec` is kept as a reference in case  
you ever port the project to Kivy/KivyMD.

---

## 📊 Adding a Custom Indicator

1. Write your formula in `custom_indicators.py`
2. Add a `@staticmethod` method in `IndicatorEngine` inside `main.py`
3. Register it in `INDICATOR_CONFIG` (same file)
4. Rebuild — the button appears automatically in the UI

---

## 📜 Permissions

| Permission | Purpose |
|---|---|
| `INTERNET` | Fetch live prices from Binance / Yahoo Finance |
| `READ_EXTERNAL_STORAGE` | Load saved settings |
| `WRITE_EXTERNAL_STORAGE` | Save user settings (timeframe, indicators) |
