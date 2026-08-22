[app]

title = PSX AI Intelligence
package.name = psxai
package.domain = org.psxai

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt,md

version = 1.0.0

# Current application does not require python-dotenv.
requirements = python3,kivy,requests

# Keep p4a aligned with the working operational application.
p4a.branch = v2024.01.21

orientation = portrait
fullscreen = 0

# Android build target
android.api = 33
android.minapi = 21

# Keep the same working Android toolchain.
android.ndk = 25b
android.sdk = 33
android.build_tools_version = 33.0.2

android.accept_sdk_license = True

# PSX / Yahoo Finance / Grok API network access
android.permissions = INTERNET

# Common ARM architectures
android.archs = arm64-v8a,armeabi-v7a

# Exclude development/build files
source.exclude_dirs = .git,.buildozer,bin,__pycache__,venv,.venv,tests
source.exclude_patterns = *.pyc,*.pyo,*~,*.bak

[buildozer]

log_level = 2
warn_on_root = 0
