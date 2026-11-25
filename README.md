# world-at-a-glance

[![make.fun · news-image-20261125](https://make.fun/badge/news-image-20261125.svg)](https://make.fun/bounty/news-image-20261125?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125)
[![rank](https://make.fun/badge/news-image-20261125/nmlyz/world-at-a-glance/rank.svg)](https://make.fun/bounty/news-image-20261125/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125)
[![reward](https://make.fun/badge/news-image-20261125/nmlyz/world-at-a-glance/reward.svg)](https://make.fun/bounty/news-image-20261125?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125)

A single-file Python program that draws a newspaper front page summing up the world news of Wednesday 25 November 2026 — three oil tankers hitting mines in the Strait of Hormuz, Nvidia shares cooling after Jensen Huang's return, a Russian drone entering Polish airspace, Shanghai's party chief under investigation, SpaceX and Tesla moving toward a merger, a deadly strike in Gaza, Sanofi's $41 billion purchase of Insmed, and a fatal blast in Hanoi — as one 1024x1024 PNG, drawn entirely with code (a hand-made bitmap font and eight spot illustrations, no external assets) using only the Python standard library.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

The program writes `entry.png` to the output directory. It uses no network and is fully deterministic: every run produces the same bytes.
