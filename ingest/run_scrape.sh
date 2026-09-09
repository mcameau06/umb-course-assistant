#!/bin/bash
set -e
cd "$(dirname "$0")/.."
source myenv/bin/activate
python -m ingest.scraper --level ugrd --max-majors 5
