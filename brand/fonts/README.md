# Fonts used by the brand kit

`kit.py` and `thumb.py` expect these three files next to them in `fonts/`.
They are not committed (binary, and freely downloadable). Fetch them from
Google Fonts before running either script:

```bash
cd brand/fonts
curl -sSLO https://github.com/google/fonts/raw/main/ofl/anton/Anton-Regular.ttf
curl -sSLO https://github.com/google/fonts/raw/main/ofl/bebasneue/BebasNeue-Regular.ttf
curl -sSL -o 'Montserrat[wght].ttf' \
  'https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat%5Bwght%5D.ttf'
```

All three are SIL Open Font License 1.1.

| File | Used for |
|---|---|
| `Anton-Regular.ttf` | display / hook lines on covers |
| `Montserrat[wght].ttf` | card body, captions, UI pills (weight 800) |
| `BebasNeue-Regular.ttf` | the closing question strip on thumbnails |

Both scripts resolve `fonts/` relative to the working directory, so run them
from inside `brand/`:

```bash
cd brand && python kit.py     # writes kit/*.jpg, kit/*.png
cd brand && python thumb.py
```

They need Pillow only (`pip install pillow`).
