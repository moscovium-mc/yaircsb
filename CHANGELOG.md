# Changelog

## YAIRCSB - Yet Another IRC Spam Bot

### Added Features
- **Local Art Support** - Drop your own `.txt` files in `custom_art/` and they're instantly available alongside the remote art collection
- **Spam Bomb** - Admin command `!spam bomb` unleashes 10 random arts in rapid succession
- **Repeat Mode** - Admin command `!spam repeat <1-100>` lets you loop any art multiple times
- **Speed Display** - `!spam speed` shows current lines per second, command delay, and repeat count
- **Ban Detection & Auto-Rejoin** - Bot detects bans and attempts to rejoin with exponential backoff
- **Channel Mode Tracking** - Monitors +m (moderated) mode and warns before sending messages
- **Enhanced Command Prefix** - Uses `!spam` instead of `.ascii` for a cleaner interface
- **Custom Help System** - Built-in `help.txt` support with fallback to hardcoded help text

### Changed Features
- **Faster Spam Speed** - Reduced message delay from 0.5s to 0.1s and flood delay from 1s to 0.5s
- **Improved Database Sync** - Added branch support and better pagination handling
- **Multiple Channel Support** - Can join multiple channels at once (comma-separated list)
- **NickServ Authentication** - Fixed to send password only (no nickname required)
- **Better Error Handling** - More graceful handling of connection issues and network errors

### Modified Behavior
- **Local Files Priority** - Local art files in `custom_art/` take precedence over remote files
- **Recursive Art Scanning** - Supports nested folders in `custom_art/` directory
- **Exact Name Matching** - `!spam <name>` now searches root directory first for exact matches
- **Improved Admin Detection** - More wildcard pattern matching for admin masks

### Fixed Issues
- **Hostname Detection** - Properly captures hostmask for ban detection
- **Join Synchronization** - Waits for MOTD before joining channels
- **Connection Resilience** - Better reconnection logic with state cleanup
- **Unicode Handling** - Improved encoding detection for local files
