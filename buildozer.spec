[app]

title = Chladroid

package.name = chladni.forandroid

package.domain = com.jarredapps

source.dir = .

version = 1.0

source.include_exts = py,png,jpg,jpeg,kv,atlas

requirements = python3,pygame-ce,sdl2,sdl2_image,sdl2_mixer,sdl2_ttf,pyjnius

orientation = landscape

fullscreen = 1

icon.filename = %(source.dir)s/data/icon.jpg

#presplash.filename = %(source.dir)s/data/presplash.png

#presplash.color = #550000

android.api = 35

android.minapi = 24

android.archs = arm64-v8a

android.accept_sdk_license = True

#android.entrypoint = org.kivy.android.PythonActivity

android.permissions = RECORD_AUDIO

p4a.bootstrap = sdl2

# master is already the stable default.
p4a.branch = master

log_level = 2

warn_on_root = 1
