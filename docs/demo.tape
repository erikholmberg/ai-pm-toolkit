# VHS tape for docs/demo.gif — the connector pipeline in three beats.
#
# Regenerate:  vhs docs/demo.tape     (run from the repo root)
# Install:     brew install vhs
#
# Everything here runs against the bundled fixture, so this renders from a
# clean clone with no credentials and no network.

Output docs/demo.gif

Set Shell "bash"
Set FontSize 15
Set Width 1240
Set Height 875
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 22ms
Set PlaybackSpeed 1.0

Hide
Type "clear" Enter
Show

Sleep 800ms

# Beat 1 — pull issues out of Jira into the canonical shape.
Type "python3 connectors/fetch.py jira issues --offline --with-started --out issues.csv"
Sleep 400ms
Enter
Sleep 2500ms

# Beat 2 — the canonical columns every script already reads.
Type "cut -d, -f1,2,3,7,12 issues.csv | column -s, -t | head -5"
Sleep 400ms
Enter
Sleep 2500ms

# Beat 3 — the payoff: a real analysis, no hand-built CSV.
Type "python3 scripts/cycle-lead-time-analyzer.py --csv issues.csv | head -24"
Sleep 400ms
Enter
Sleep 4500ms

# The demo writes issues.csv into the repo root; don't leave it behind.
Hide
Type "rm -f issues.csv issues.csv.meta.json" Enter
Show
