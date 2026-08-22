# PSX AI Trading Intelligence

## GitHub → APK

Upload the contents of this folder to the ROOT of a new GitHub repository.

The included GitHub Actions workflow builds a debug APK automatically.

### Build manually

```bash
buildozer android clean
buildozer -v android debug
```

### GitHub Actions

Push to `main`, or open:
Actions → Build Android APK → Run workflow.

The generated APK will be available under the workflow Artifacts as:
`psx-ai-debug-apk`

### Important
Do not commit real API keys. This project is currently at the data-engine foundation stage. No fake market data or BUY/SELL recommendations are included.
