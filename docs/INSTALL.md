# Installing & playing TYPEFASTER

A terminal typing game. Works offline instantly; multiplayer if you point it at
a server.

## Install

**Homebrew (macOS / Linux):**
```bash
brew install Anoshor/typefaster/typefaster
```

**pipx (any OS with Python 3.11+):**
```bash
pipx install typefaster-cli
```

Verify:
```bash
typefaster version
```

## Play offline (no account, no internet)
```bash
typefaster                 # main menu — Quick Race, Time Attack, Practice, Daily…
typefaster race            # jump straight into a quote race
typefaster race --mode time --time 60
typefaster stats           # your progress
```

## Play online (multiplayer)
The client ships pointing at the public server by default, so:
```bash
typefaster register <name>           # create an account (password)
# or social login:
typefaster login --github
typefaster login --google

typefaster lobby create --name Friday --time 60   # host a lobby (shows a join code)
typefaster lobby join ABC123                        # friends join with the code
typefaster lobby list                               # browse public lobbies
typefaster leaderboard global                       # global | daily | weekly
```
In the lobby waiting room, press **R** to ready; the server starts the race when
everyone is ready. Press **Esc** to leave.

Point at a different server (self-hosted / local):
```bash
typefaster config set-server https://your-server.example.com
typefaster config show
```

## Update
```bash
brew upgrade typefaster          # Homebrew
pipx upgrade typefaster-cli      # pipx
```

## Uninstall
```bash
brew uninstall typefaster
# or
pipx uninstall typefaster-cli
```
