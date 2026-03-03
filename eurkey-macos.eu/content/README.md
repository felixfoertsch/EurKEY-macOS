# EurKEY-macOS

The Keyboard Layout for Europeans, Coders and Translators. This repo is a fork and contains a **modified verison** of the EurKEY base layout.

I start versioning my customized edition from 2, since the layout is based on my modified EurKEY v1.4 that I have been using the last few years. The version with slight fixes is now available is called v1.5.

EurKEY-macOS is a rework targeted at MacBooks with the with pyhiscal English International keyboard (ISO). Since it is an ISO layout, it has one additional key (`) and the big Enter key.

The keyboard layout should be compatible with the other ISO layouts typically available in Europe (e.g. German ISO). I tested the layout on the current tenkeyless MacBook keyboard (MacBook Air 2024). Working numpad keys are therefore not guaranteed.

## Installation

- Download the `EurKEY.bundle` file.
- Copy the `EurKEY.bundle` file to `/Library/Keyboard Layouts/` (for global installation) or `~/Library/Keyboard Layouts/` (for user installation).
- Open System Settings > Keyboard > Input Sources <br><img src="eurkey-macos.eu/static/img/1-input-sources.png" width="300">
- Click the `+` button <br><img src="eurkey-macos.eu/static/img/2-add-layout.png" width="300">
- Add `EurKEY` from the list of available input sources <br><img src="eurkey-macos.eu/static/img/3-select-eurkey.png" width="300">
- Select `EurKEY` as the input method <br><img src="eurkey-macos.eu/static/img/4-select-input-method.png" width="300">

## Changelog

### v2.0 (WIP)

| Key Combinations | Dead Key Symbol |
| ---------------- | --------------- |
| ⌥`               | `               |
| ⌥⇧`             | ~               |
| ⌥'               | ´               |
| ⌥⇧'             | ¨               |
| ⌥6               | ^               |
| ⌥⇧6             | ˇ               |
| ⌥7               | ˚               |
| ⌥⇧7             | ¯               |
| ⌥m               | Ω               |
| ⌥⇧m             | √               |
| ⌥\               | ¬               |

### v1.5

- Configures every key exactly as it is printed on the keyboard (English - International).
- Fixes §-Key.
- Fixes German ẞ-Character ("Großes scharfes S"). Now correctly available via ⌥⇧s.
- Removes distiction between left/right modifier keys.
- Uses the `*.bundle` format to group the layout versions.
- Adds new nicer flag icon from upstream.

### v1.4

- Switches behaviour of superscript and subscript numbers: The subscript numbers are the default; the superscript numbers are available via `⌥⇧<number>`.

## Attribution

You can find the original EurKEY layout on [Steffen Brüntjens Website](https://eurkey.steffen.bruentjen.eu/start.html). My modified versions are originally based on the work of [Leonardo Brondani Schenkel](https://github.com/lbschenkel/EurKEY-Mac).

## License

- The EurKEY Layout is licensed under [GPLv3](http://www.gnu.org/licenses/gpl-3.0.html). See: [https://eurkey.steffen.bruentjen.eu/license.html](https://eurkey.steffen.bruentjen.eu/license.html).
- The EU flag icon is taken from [Iconspedia](http://www.iconspedia.com/pack/european-flags-1631/), created by [Alpak](http://alpak.deviantart.com/) and licensed under [CC](http://creativecommons.org/licenses/by-nc-nd/3.0).
