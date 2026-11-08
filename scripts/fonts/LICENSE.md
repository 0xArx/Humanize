# Bundled fonts

The dashboard serves these from your own machine so it works offline and makes no third-party requests.
Latin subset only, WOFF2.

| Font | Files | License |
|------|-------|---------|
| Instrument Serif | `InstrumentSerif-400.woff2`, `InstrumentSerif-400i.woff2` | SIL Open Font License 1.1 |
| IBM Plex Sans (variable, 400 to 600) | `IBMPlexSans.woff2` | SIL Open Font License 1.1 |
| IBM Plex Mono | `IBMPlexMono-400.woff2`, `IBMPlexMono-500.woff2` | SIL Open Font License 1.1 |

Instrument Serif is copyright the Instrument Serif Project Authors (https://github.com/Instrument/instrument-serif).
IBM Plex is copyright IBM Corp. (https://github.com/IBM/plex).
The license text is at https://openfontlicense.org/open-font-license-official-text/ and applies to these files.

---

## TrueType/OpenType files for card rendering (ttf/)

These are full TrueType and variable-font files used by the business card renderer (scripts/card.py).
The card renderer uses Pillow with FreeType and raqm for text layout.

| Font | Files | License |
|------|-------|---------|
| Instrument Serif | `ttf/InstrumentSerif-Regular.ttf`, `ttf/InstrumentSerif-Italic.ttf` | SIL Open Font License 1.1 |
| IBM Plex Sans (variable, 400 to 600) | `ttf/IBMPlexSans-Variable.ttf` | SIL Open Font License 1.1 |
| IBM Plex Mono | `ttf/IBMPlexMono-Regular.ttf`, `ttf/IBMPlexMono-Medium.ttf` | SIL Open Font License 1.1 |
| Noto Naskh Arabic (variable, Arabic script fallback) | `ttf/NotoNaskhArabic-Variable.ttf` | SIL Open Font License 1.1 |

Copyright notices, exactly as stated in each font's OFL.txt:

Instrument Serif: Copyright 2022 The Instrument Serif Project Authors (https://github.com/Instrument/instrument-serif)

IBM Plex Sans and IBM Plex Mono: Copyright 2017 IBM Corp. with Reserved Font Name "Plex"

Noto Naskh Arabic: Copyright 2022 The Noto Project Authors (https://github.com/notofonts/arabic)

All four families are licensed under the SIL Open Font License, Version 1.1.
The full license text is at https://openfontlicense.org/open-font-license-official-text/.
