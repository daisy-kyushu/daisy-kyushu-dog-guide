name: Update Events

on:
  workflow_dispatch:
  schedule:
    - cron: "40 0 * * *"

permissions:
  contents: write

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"

      - name: Update events
        run: node scripts/update-events.js

      - name: Commit changes
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "Update event data"
          file_pattern: data/events.json
