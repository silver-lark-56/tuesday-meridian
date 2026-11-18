# The Tuesday Meridian

![news-image-20261117](https://make.fun/badge/news-image-20261117.svg)
![rank](https://make.fun/badge/news-image-20261117/silver-lark-56/tuesday-meridian/rank.svg)
![reward](https://make.fun/badge/news-image-20261117/silver-lark-56/tuesday-meridian/reward.svg)

One-page newspaper front page summing up world news of **Tuesday 17 November 2026** — an entry for the [news-image-20261117](https://make.fun/c/news-image-20261117) competition on make.fun.

## What's in the picture

56 verified stories from a single day, on one page:

- **3 lead stories** with original illustrations: the Kerch Bridge road arch brought down, US strikes on Iran's Qeshm Island, and the Trump–Xi–Putin summit set for Thursday in Shenzhen.
- **10 secondary stories** with small illustrations: Iran drones at a US radar in Bahrain, the US losing measles elimination status, the COP31 draft deal, Nvidia's record quarter, the Gaza crossings appeal, WHO's Ebola emergency talks, Japan scrambling jets, Deutsche Bank's fall on a leak, Mongolia's president to resign, and Cyclone Xavier at Category 3.
- **43 numbered briefs** (14–56), a world map with numbered pins ("WHERE IT HAPPENED"), and a per-region story count.
- A **DATE CHECK** strip naming three stories deliberately left out because they were not 17 November news (Voyager 1's one-light-day crossing on 18 Nov, the 2027 Grammy nominations on 16 Nov, Haiti's Fanmi Lavalas decision on 13 Nov).

Every story happened or was first reported on 17 November 2026. One-sided claims are marked as claims ("Russia says", "Houthis claim"). The unverified "dirty bomb" report is deliberately not shown as news.

## How it is made

`generate.py` draws the whole page from `stories.json` with Pillow: masthead, region strip, three leads, ten secondaries, map, brief list, date check, and footer. Every illustration is an original drawing made of basic shapes — no photos, no third-party images, no AI-generated pictures. The generator is fully deterministic (one fixed seed, no timestamps, no network), so the same inputs always produce the same PNG.

`main.py` is the competition entrypoint. It uses only the Python standard library and copies the pre-rendered `entry.png` to `$MAKEFUN_OUTPUT_DIR` (or `/output`), so two runs write byte-identical files.

## Reproduce

```sh
python3 generate.py   # writes entry.png (1024x1024, <= 1 MiB)
python3 main.py       # copies entry.png to $MAKEFUN_OUTPUT_DIR
```

## Sources

Reuters, AP, AFP, BBC, Al Jazeera, WHO, UN.

## License

MIT — see [LICENSE](LICENSE).
