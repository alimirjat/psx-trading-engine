[app]
title = PSX AI Trading Intelligence
package.name = psxai
package.domain = org.psxai
source.dir = .
source.include_exts = py,json,txt
version = 0.1.0

requirements = python3,kivy,requests

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,POST_NOTIFICATIONS

[buildozer]
log_level = 2
warn_on_root = 1
