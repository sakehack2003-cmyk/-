#!/usr/bin/env bash
set -euo pipefail
# Requires inkscape command
mkdir -p exports
for f in lp_creative_01_hero.svg lp_creative_02_features.svg lp_creative_03_cta.svg split_items/feature_01.svg split_items/feature_02.svg split_items/feature_03.svg; do
  out="exports/$(basename "${f%.svg}").png"
  inkscape "$f" --export-type=png --export-filename="$out" >/dev/null 2>&1
  echo "exported: $out"
done
