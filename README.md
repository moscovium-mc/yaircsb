# YAIRCSB

YAIRCSB (Yet Another IRC Spam Bot) is a souped up IRC bot that pumps ASCII art like there's no tomorrow! Based on the legendary Scroll bot, YAIRCSB brings all the art you love plus the ability to use your own custom creations. Built to be fast, stable, and ready to spam your channels with beautiful (and sometimes questionable) ASCII masterpieces.

All the remote art is loaded directly from the [ircart](https://git.supernets.org/ircart/ircart) repository, but you can also store your own art locally in `custom_art/`. Whenever the repository updates, just `!spam sync` and you'll have access to the freshest art packs!

No API keys, no complicated setup, no excuses not to get this bad boy pumping in your channels today!

## Dependencies
* [python](https://www.python.org/) (3.6+)
* [aiohttp](https://pypi.org/project/aiohttp/) - `pip install aiohttp`
* [chardet](https://pypi.org/project/chardet/) - `pip install chardet`

## Quick Start
1. Clone the repository
2. Edit the configuration at the top of `yaircsb.py`:
   - Set your server, channels, and nickname
   - Configure your admin mask (nick!user@host)
   - Set your NickServ password if needed
3. Run: `python yaircsb.py`

## Commands
| Command | Description |
|---------|-------------|
| `!spam help` | this help message |
| `!spam <name>` | play the art file |
| `!spam dirs` | list available art directories |
| `!spam list` | show the art file list URL |
| `!spam play <url>` | play from a raw pastebin URL |
| `!spam random [dir\|query]` | play random art, optionally from a directory or search |
| `!spam search <query>` | search for art matching the query |
| `!spam speed` | show current spam speed stats |
| `!spam stop` | stop playing art immediately |

### Admin Commands
| Command | Description |
|---------|-------------|
| `!spam bomb` | unleash 10 random arts in rapid succession |
| `!spam repeat <1-100>` | set how many times to repeat each art |
| `!spam sync` | sync the art database for the freshest art |
| `!spam settings [<setting> <option>]` | view or modify bot settings |

## Settings
| Setting | Type | Description |
|---------|------|-------------|
| `flood` | int/float | delay between commands (seconds) |
| `ignore` | str | directories to ignore in random (comma-separated) |
| `lines` | int | max lines allowed outside of #scroll |
| `msg` | int/float | delay between each line of art (seconds) |
| `paste` | bool | enable/disable `!spam play` |
| `results` | int | max results to show in search |

## Custom Art
Want to use your own art? Just drop your `.txt` files in the `custom_art/` directory. YAIRCSB will automatically detect them and make them available alongside the remote collection. Nested folders are supported too!

## Features
- **Lightning Fast** - Default spam speed of 0.1s between lines, 0.5s command flood protection
- **Smart Ban Detection** - Automatically detects bans and tries to rejoin with exponential backoff
- **Channel Mode Awareness** - Knows when channels are moderated (+m) and warns appropriately
- **Local Art First** - Your custom art takes priority over remote files
- **Multiple Channels** - Join and spam in as many channels as you want
- **Auto-Rejoin** - Tries to rejoin if kicked (with style)

## Admin Mask
The admin mask uses wildcard patterns in `nick!user@host` format:
- `*` matches anything
- `?` matches any single character
- Example: `yaircsb!*@*` would match any yaircsb from any host


---

###### Based on Scroll by acidvegas • Modified by moscovium-mc • ASCII Art from [ircart](https://git.supernets.org/ircart/ircart)