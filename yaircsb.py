#!/usr/bin/env python
# YAIRCSB - Yet Another IRC Spam Bot - Based on Scroll by acidvegas - github.com/acidvegas
# Modified by moscovium-mc - github.com/moscovium-mc

import asyncio
import random
import re
import ssl
import time
import urllib.request
import os

try:
	import aiohttp
except ImportError:
	raise SystemExit('missing required aiohttp library (pip install aiohttp)')

try:
	import chardet
except ImportError:
	raise SystemExit('missing required chardet library (pip install chardet)')


class connection:
	server  = ''
	port    = 6697
	ipv6    = False
	ssl     = True
	vhost   = None
	channel = '#'
	key     = None
	modes   = 'BdDg'

class identity:
	nickname = 'yaircsb'
	username = 'yaircsb'
	realname = 'yaircsb'
	nickserv = ''  # Password for NickServ

class repo:
	url = 'https://git.supernets.org/'
	repo = 'ircart/ircart'
	branch = 'master'


# Settings
admin = ''
custom_art_dir = 'custom_art'


# Formatting Characters
bold        = '\x02'
italic      = '\x1D'
underline   = '\x1F'
reverse     = '\x16'
reset       = '\x0f'
white       = '00'
black       = '01'
blue        = '02'
green       = '03'
red         = '04'
brown       = '05'
purple      = '06'
orange      = '07'
yellow      = '08'
light_green = '09'
cyan        = '10'
light_cyan  = '11'
light_blue  = '12'
pink        = '13'
grey        = '14'
light_grey  = '15'


def color(msg, foreground, background=None):
	return f'\x03{foreground},{background}{msg}{reset}' if background else f'\x03{foreground}{msg}{reset}'

def debug(data):
	print('{0} | [~] - {1}'.format(time.strftime('%I:%M:%S'), data))

def error(data, reason=None):
	print('{0} | [!] - {1} ({2})'.format(time.strftime('%I:%M:%S'), data, str(reason))) if reason else print('{0} | [!] - {1}'.format(time.strftime('%I:%M:%S'), data))

def get_url(url, git=False):
	data = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'}
	if git:
		data['Accept'] = 'application/vnd.github.v3+json'
	req = urllib.request.Request(url, headers=data)
	return urllib.request.urlopen(req, timeout=10)

def is_admin(ident):
	return re.compile(admin.replace('*','.*')).search(ident)

def ssl_ctx():
	ctx = ssl.create_default_context()
	ctx.check_hostname = False
	ctx.verify_mode = ssl.CERT_NONE
	return ctx

class Bot():
	def __init__(self):
		self.db              = None
		self.last            = time.time()
		self.loops           = dict()
		self.host            = ''
		self.playing         = False
		self.repeat_count    = 1
		self.settings        = {
			'flood'        : 0.5,
			'ignore'       : '',
			'lines'        : 500,
			'msg'          : 0.1,
			'paste'        : True,
			'results'      : 25}
		self.slow            = False
		self.reader          = None
		self.writer          = None
		self.registered      = False
		self.channel_modes   = {}  # Track channel modes: {'#channel': {'moderated': False, 'banned': False}}
		self.ban_retry_count = {}  # Track ban retry attempts per channel

	async def raw(self, data):
		self.writer.write(data[:510].encode('utf-8') + b'\r\n')
		await self.writer.drain()

	async def action(self, chan, msg):
		await self.sendmsg(chan, f'\x01ACTION {msg}\x01')

	async def sendmsg(self, target, msg):
		# Check if channel is moderated before sending
		if target in self.channel_modes and self.channel_modes[target].get('moderated', False):
			# In moderated mode, only ops/voiced can speak
			debug(f'Channel {target} is moderated (+m), message may not be delivered')
		
		# Check if banned
		if target in self.channel_modes and self.channel_modes[target].get('banned', False):
			debug(f'Cannot send to {target}: bot is banned')
			return False
		
		await self.raw(f'PRIVMSG {target} :{msg}')
		return True

	async def irc_error(self, chan, msg, reason=None):
		await self.sendmsg(chan, '[{0}] {1} {2}'.format(color('ERROR', red), msg, color(f'({reason})', grey))) if reason else await self.sendmsg(chan, '[{0}] {1}'.format(color('ERROR', red), msg))

	async def connect(self):
		while True:
			try:
				options = {
					'host'       : connection.server,
					'port'       : connection.port,
					'limit'      : 1024,
					'ssl'        : ssl_ctx() if connection.ssl else None,
					'family'     : 10 if connection.ipv6 else 2,
					'local_addr' : connection.vhost
				}
				self.reader, self.writer = await asyncio.wait_for(asyncio.open_connection(**options), 15)
				await self.raw(f'USER {identity.username} 0 * :{identity.realname}')
				await self.raw('NICK ' + identity.nickname)
			except Exception as ex:
				error('failed to connect to ' + connection.server, ex)
			else:
				await self.listen()
			finally:
				for item in self.loops:
					if self.loops[item]:
						self.loops[item].cancel()
				self.loops   = dict()
				self.playing = False
				self.slow    = False
				self.registered = False
				self.channel_modes = {}
				self.ban_retry_count = {}
				await asyncio.sleep(30)

	async def scan_local_art(self):
		"""Scan custom_art folder for local ascii txt files and add to database"""
		if not os.path.exists(custom_art_dir):
			os.makedirs(custom_art_dir)
			debug(f'created {custom_art_dir} directory')
			return
		
		local_count = 0
		
		# Custom_art directory recursively
		for root, dirs, files in os.walk(custom_art_dir):
			for file in files:
				if file.endswith('.txt'):
					# Get relative path from custom_art directory
					rel_path = os.path.relpath(os.path.join(root, file), custom_art_dir)
					name = rel_path[:-4]  # Remove .txt extension
					
					# Add all local files directly to root for playing
					if name not in self.db['root']:
						self.db['root'].append(name)
						local_count += 1
		
		if local_count > 0:
			debug(f'scanned local art: found {local_count} files in {custom_art_dir}/ (added to root)')

	async def sync(self):
		self.db = {'root': []}
		
		# First, sync remote database
		page = 1
		per_page = 1000
		
		while True:
			try:
				timeout = aiohttp.ClientTimeout(total=30)
				headers = {'User-Agent': 'yaircsb/1.0'}
				async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
					async with session.get(f'{repo.url}/api/v1/repos/{repo.repo}/git/trees/{repo.branch}?recursive=1&page={page}&per_page={per_page}', ssl=False) as resp:
						if resp.status != 200:
							error('failed to sync database', await resp.text())
							return
						files = await resp.json()
						
						for file in files['tree']:
							if file['path'].startswith('ircart/') and file['path'].endswith('.txt') and not file['path'].startswith('ircart/.'):
								name = file['path'][7:-4]
								if '/' in name:
									dir_name, fname = name.split('/', 1)
									self.db[dir_name] = self.db[dir_name]+[fname,] if dir_name in self.db else [fname,]
								else:
									self.db['root'].append(name)
						
						if not files.get('truncated', False):
							break
						
						page += 1

			except Exception as ex:
				error('failed to sync remote database', ex)
				return
		
		# Now scan local custom_art folder
		await self.scan_local_art()

	async def play(self, chan, name, paste=False):
		local_path = None
		
		# Check for help file
		if name == 'help':
			local_path = 'help.txt'
		else:
			# Check for local file directly in custom_art directory (supports nested folders)
			local_file_path = os.path.join(custom_art_dir, name.replace('/', os.path.sep) + '.txt')
			if os.path.exists(local_file_path):
				local_path = local_file_path
		
		if local_path and os.path.exists(local_path):
			try:
				with open(local_path, 'r', encoding='utf-8', errors='replace') as f:
					lines = f.read().splitlines()
				
				if len(lines) > int(self.settings['lines']) and chan != '#scroll':
					await self.irc_error(chan, 'file is too big', f'take those {len(lines):,} lines to #scroll')
				else:
					if name != 'help':
						await self.action(chan, 'playing local art: ' + color(name, cyan))
					for _ in range(self.repeat_count):
						for line in lines:
							line = line.replace('\n','').replace('\r','')
							await self.sendmsg(chan, line + reset)
							if self.settings['msg'] > 0:
								await asyncio.sleep(self.settings['msg'])
			except Exception as ex:
				await self.irc_error(chan, f'error playing local {name}', ex)
			finally:
				self.playing = False
				return
		
		# If not found locally, try remote
		try:
			if paste:
				ascii = get_url(name)
			else:
				ascii = get_url(f'{repo.url}/{repo.repo}/raw/{repo.branch}/ircart/{name}.txt')
			
			if ascii.getcode() == 200:
				raw = ascii.read()
				encoding = chardet.detect(raw)['encoding'] or 'utf-8'
				lines = raw.decode(encoding, errors='replace').splitlines()
				if len(lines) > int(self.settings['lines']) and chan != '#scroll':
					await self.irc_error(chan, 'file is too big', f'take those {len(lines):,} lines to #scroll')
				else:
					if not paste:
						await self.action(chan, 'the ascii gods have chosen... ' + color(name, cyan))
					for _ in range(self.repeat_count):
						for line in lines:
							line = line.replace('\n','').replace('\r','')
							await self.sendmsg(chan, line + reset)
							if self.settings['msg'] > 0:
								await asyncio.sleep(self.settings['msg'])
			else:
				await self.irc_error(chan, 'invalid name', name) if not paste else await self.irc_error(chan, 'invalid url', name)
		except Exception as ex:
			try:
				await self.irc_error(chan, f'error playing {name}', ex)
			except:
				error(f'error playing {name}', ex)
		finally:
			self.playing = False

	async def spam_bomb(self, chan):
		await self.sendmsg(chan, bold + color('>>> SPAM BOMB ACTIVATED <<<', red))
		for i in range(10):
			choices = [item for item in self.db if item not in self.settings['ignore'].split(',') and self.db[item]]
			if choices:
				query = random.choice(choices)
				if query in self.db and self.db[query]:
					ascii_name = f'{query}/{random.choice(self.db[query])}'
					await self.action(chan, f'spam bomb round {i+1}/10: ' + color(ascii_name, cyan))
					self.playing = True
					await self.play(chan, ascii_name)
					await asyncio.sleep(0.3)
		await self.sendmsg(chan, bold + color('>>> SPAM BOMB COMPLETE <<<', red))

	async def show_help(self, chan):
		if os.path.exists('help.txt'):
			self.playing = True
			await self.play(chan, 'help')
		else:
			help_text = [
				f"{bold}YAIRCSB Commands:{reset}",
				f"!spam help                          | this help",
				f"!spam <name>                        | play art",
				f"!spam bomb                          | 10 random arts (admin)",
				f"!spam dirs                          | list directories",
				f"!spam list                          | list art files",
				f"!spam play <url>                    | play from url",
				f"!spam random [dir]                  | random art",
				f"!spam repeat <1-100>                | set repeat count (admin)",
				f"!spam search <query>                | search art",
				f"!spam settings                      | view settings",
				f"!spam speed                         | show spam speed",
				f"!spam stop                          | stop playing",
				f"!spam sync                          | sync database (admin)",
				f"",
				f"{color('Admin:', yellow)} {color(admin, cyan)}"
			]
			for line in help_text:
				await self.sendmsg(chan, line)
				await asyncio.sleep(0.1)

	async def join_channels(self):
		channels = connection.channel.split(',')
		for channel in channels:
			channel = channel.strip()
			await self.raw(f'JOIN {channel}')
			await asyncio.sleep(1)
			debug(f'joined {channel}')
			# Initialize channel mode tracking
			if channel not in self.channel_modes:
				self.channel_modes[channel] = {'moderated': False, 'banned': False}

	async def handle_ban(self, chan):
		"""Handle when bot gets banned from a channel"""
		self.channel_modes[chan]['banned'] = True
		debug(f'Bot banned from {chan}')
		
		# Track retry attempts
		if chan not in self.ban_retry_count:
			self.ban_retry_count[chan] = 0
		
		# Try to rejoin with backoff
		self.ban_retry_count[chan] += 1
		retry_delay = min(300, 30 * (2 ** (self.ban_retry_count[chan] - 1)))  # 30, 60, 120, 240, 300 max
		
		await self.sendmsg(chan, f'{color("[", red)}BANNED{color("]", red)} I\'ll try to return in {retry_delay} seconds...')
		await asyncio.sleep(retry_delay)
		
		# Attempt to rejoin
		await self.raw(f'JOIN {chan}')
		debug(f'Attempting to rejoin {chan} after ban (attempt {self.ban_retry_count[chan]})')

	async def handle_unban(self, chan):
		"""Handle when bot gets unbanned"""
		if chan in self.channel_modes:
			self.channel_modes[chan]['banned'] = False
		if chan in self.ban_retry_count:
			del self.ban_retry_count[chan]
		debug(f'Bot unbanned from {chan}')

	async def listen(self):
		while True:
			try:
				if self.reader.at_eof():
					break
				data = await asyncio.wait_for(self.reader.readuntil(b'\r\n'), 600)
				line = data.decode('utf-8').strip()
				args = line.split()
				debug(line)
				
				if line.startswith('ERROR :Closing Link:'):
					error('Connection closed by server')
					break
				elif args[0] == 'PING':
					await self.raw('PONG ' + args[1][1:] if len(args) > 1 else 'PONG')
				elif args[1] == '001':
					if connection.modes:
						await self.raw(f'MODE {identity.nickname} +{connection.modes}')
					if identity.nickserv and identity.nickserv != 'changeme':
						await self.sendmsg('NickServ', f'IDENTIFY {identity.nickserv}')
						await asyncio.sleep(2)
					self.registered = True
				elif args[1] == '376' or args[1] == '422':
					if self.registered:
						await self.join_channels()
						await self.sync()
				elif args[1] == '433':
					error('Nickname already in use')
					break
				elif args[1] == 'INVITE' and len(args) == 4:
					invited = args[2]
					chan = args[3][1:]
					if invited == identity.nickname:
						await self.raw(f'JOIN {chan}')
				elif args[1] == 'JOIN' and len(args) >= 3:
					nick = args[0].split('!')[0][1:]
					chan = args[2]
					if nick == identity.nickname:
						self.host = args[0].split('@')[1] if '@' in args[0] else ''
						# Reset ban status when successfully joined
						if chan in self.channel_modes:
							self.channel_modes[chan]['banned'] = False
						if chan in self.ban_retry_count:
							del self.ban_retry_count[chan]
						debug(f'Successfully joined {chan}')
				elif args[1] == 'KICK' and len(args) >= 4:
					chan = args[2]
					kicked = args[3]
					if kicked == identity.nickname:
						await asyncio.sleep(1)
						await self.sendmsg(chan, f'{color("[", red)}REVENGE{color("]", red)} {bold}I\'LL BE BACK{reset}')
						await asyncio.sleep(2)
						await self.raw(f'JOIN {chan}')
				# Handle MODE changes
				elif args[1] == 'MODE' and len(args) >= 4:
					target = args[2]
					mode_changes = args[3]
					
					# Check if this is a channel mode
					if target.startswith('#'):
						# Initialize channel tracking if needed
						if target not in self.channel_modes:
							self.channel_modes[target] = {'moderated': False, 'banned': False}
						
						# Parse mode changes
						adding = True
						for char in mode_changes:
							if char == '+':
								adding = True
							elif char == '-':
								adding = False
							elif char == 'm':
								# Moderated mode
								self.channel_modes[target]['moderated'] = adding
								debug(f'Channel {target} moderated mode {"enabled" if adding else "disabled"}')
								if adding:
									await self.sendmsg(target, f'{color("[", yellow)}NOTICE{color("]", yellow)} Channel is now moderated (+m)')
							elif char == 'b':
								# Ban mode - need to check 
								if len(args) > 4:
									ban_mask = args[4]
									# Check if ban matches our hostmask
									our_mask = f'{identity.nickname}!{identity.username}@{self.host}'
									if self.match_ban_mask(ban_mask, our_mask):
										if adding:
											await self.handle_ban(target)
										else:
											await self.handle_unban(target)
				
				elif args[1] == 'PRIVMSG' and len(args) >= 4:
					ident = args[0][1:]
					nick = args[0].split('!')[0][1:]
					chan = args[2]
					msg = ' '.join(args[3:])[1:]
					
					if chan == identity.nickname:
						chan = nick
					
					if chan in connection.channel.split(',') or chan == '#scroll' or chan == nick:
						cmd_args = msg.split()
						if not cmd_args:
							continue
						
						if msg == f'@{identity.nickname}' or msg == '@scroll':
							await self.sendmsg(chan, bold + f'{identity.nickname.upper()} - Yet Another IRC Spam Bot - Based on Scroll by acidvegas')
						
						elif cmd_args[0] == '!spam':
							if len(cmd_args) < 2:
								continue
							
							subcmd = cmd_args[1].lower()
							
							if subcmd == 'help':
								await self.show_help(chan)
							
							elif subcmd == 'speed':
								lines_per_sec = 1 / self.settings['msg'] if self.settings['msg'] > 0 else 0
								await self.sendmsg(chan, f'{color("spam speed:", cyan)} {color(str(round(lines_per_sec, 1)), yellow)} lines/sec | {color(str(self.settings["flood"]), yellow)} sec cmd delay | repeat: {color(str(self.repeat_count), yellow)}x')
							
							elif subcmd == 'repeat' and len(cmd_args) == 3 and is_admin(ident):
								try:
									repeat = int(cmd_args[2])
									if 1 <= repeat <= 100:
										self.repeat_count = repeat
										await self.sendmsg(chan, f'{color("OK", light_green)} repeat set to {repeat}')
									else:
										await self.irc_error(chan, 'repeat must be 1-100')
								except ValueError:
									await self.irc_error(chan, 'invalid number', cmd_args[2])
							
							elif subcmd == 'bomb' and is_admin(ident):
								if not self.playing:
									await self.spam_bomb(chan)
								else:
									await self.irc_error(chan, 'already playing art')
							
							elif msg == '!spam stop':
								if self.playing:
									if chan in self.loops:
										self.loops[chan].cancel()
									self.playing = False
									await self.sendmsg(chan, f'{color("STOPPED", red)} art playback halted')
							
							elif not self.playing:
								if subcmd == 'dirs':
									for dir_name in self.db:
										await self.sendmsg(chan, '[{0}] {1}{2}'.format(color(str(list(self.db).index(dir_name)+1).zfill(2), pink), dir_name.ljust(10), color('('+str(len(self.db[dir_name]))+')', grey)))
										if self.settings['msg'] > 0:
											await asyncio.sleep(self.settings['msg'])
								
								elif subcmd == 'list':
									await self.sendmsg(chan, underline + color(f'{repo.url}/{repo.repo}/src/{repo.branch}/ircart/.list', light_blue))
								
								elif subcmd == 'random' and len(cmd_args) in (2,3):
									if len(cmd_args) == 3:
										query = cmd_args[2]
									else:
										choices = [item for item in self.db if item not in self.settings['ignore'].split(',') and self.db[item]]
										if not choices:
											await self.irc_error(chan, 'database is empty', 'try !spam sync')
											continue
										query = random.choice(choices)
									if query in self.db and self.db[query]:
										ascii_name = f'{query}/{random.choice(self.db[query])}'
										self.playing = True
										self.loops[chan] = asyncio.create_task(self.play(chan, ascii_name))
									else:
										results = [{'name':ascii,'dir':dir_name} for dir_name in self.db for ascii in self.db[dir_name] if query in ascii]
										if results:
											ascii_name = random.choice(results)
											ascii_name = f'{ascii_name["dir"]}/{ascii_name["name"]}'
											self.playing = True
											self.loops[chan] = asyncio.create_task(self.play(chan, ascii_name))
										else:
											await self.irc_error(chan, 'invalid directory name or search query', query)
								
								elif subcmd == 'sync' and is_admin(ident):
									await self.sync()
									await self.sendmsg(chan, bold + color('database synced', light_green))
								
								elif subcmd == 'play' and len(cmd_args) == 3 and self.settings['paste']:
									url = cmd_args[2]
									if url.startswith('https://pastebin.com/raw/') and len(url.split('raw/')) > 1:
										self.loops[chan] = asyncio.create_task(self.play(chan, url, paste=True))
									else:
										await self.irc_error(chan, 'invalid pastebin url', url)
								
								elif subcmd == 'search' and len(cmd_args) == 3:
									query = cmd_args[2]
									results = [{'name':ascii,'dir':dir_name} for dir_name in self.db for ascii in self.db[dir_name] if query in ascii]
									if results:
										for item in results[:int(self.settings['results'])]:
											if item['dir'] == 'root':
												await self.sendmsg(chan, '[{0}] {1}'.format(color(str(results.index(item)+1).zfill(2), pink), item['name']))
											else:
												await self.sendmsg(chan, '[{0}] {1} {2}'.format(color(str(results.index(item)+1).zfill(2), pink), item['name'], color('('+item['dir']+')', grey)))
											if self.settings['msg'] > 0:
												await asyncio.sleep(self.settings['msg'])
									else:
										await self.irc_error(chan, 'no results found', query)
								
								elif subcmd == 'settings':
									if len(cmd_args) == 2:
										for item in self.settings:
											await self.sendmsg(chan, color(item.ljust(13), yellow) + color(str(self.settings[item]), grey))
									elif len(cmd_args) == 4 and is_admin(ident):
										setting = cmd_args[2]
										option = cmd_args[3]
										if setting in self.settings:
											if setting in ('flood','lines','msg','results'):
												try:
													option = float(option)
													self.settings[setting] = option
													await self.sendmsg(chan, color('OK', light_green))
												except ValueError:
													await self.irc_error(chan, 'invalid option', 'must be a float or int')
											elif setting == 'paste':
												if option == 'on':
													self.settings[setting] = True
													await self.sendmsg(chan, color('OK', light_green))
												elif option == 'off':
													self.settings[setting] = False
													await self.sendmsg(chan, color('OK', light_green))
												else:
													await self.irc_error(chan, 'invalid option', 'must be on or off')
										else:
											await self.irc_error(chan, 'invalid setting', setting)
								
								elif len(cmd_args) == 2:
									query = cmd_args[1]
									# Search for match in database
									found = False
									for dir_name in self.db:
										if query in self.db[dir_name]:
											if dir_name == 'root':
												art_name = query
											else:
												art_name = f'{dir_name}/{query}'
											self.playing = True
											self.loops[chan] = asyncio.create_task(self.play(chan, art_name))
											found = True
											break
									if not found:
										await self.irc_error(chan, 'no results found', query)
			except (UnicodeDecodeError, UnicodeEncodeError):
				pass
			except Exception as ex:
				error('fatal error occured', ex)
				break
			finally:
				self.last = time.time()
	
	def match_ban_mask(self, ban_mask, our_mask):
		"""Check if a ban mask matches our hostmask"""
		# Convert wildcard mask to regex
		pattern = ban_mask.replace('.', r'\.').replace('*', '.*').replace('?', '.')
		return re.match(pattern, our_mask) is not None


if __name__ == '__main__':
	print('#'*56)
	print('#{:^54}#'.format(''))
	print('#{:^54}#'.format('YAIRCSB - Yet Another IRC Spam Bot'))
	print('#{:^54}#'.format('Based on Scroll by acidvegas'))
	print('#{:^54}#'.format('Modified by moscovium-mc'))
	print('#{:^54}#'.format(' ASCII Art https://git.supernets.org/ircart/scroll'))
	print('#{:^54}#'.format(''))
	print('#{:^54}#'.format('ONE BOT TO RULE THEM ALL'))
	print('#{:^54}#'.format('https://github.com/moscovium-mc/yaircsb'))
	print('#{:^54}#'.format('flood: 0.5s | msg: 0.1s'))
	print('#{:^54}#'.format('command: !spam'))
	print('#{:^54}#'.format('local art: ./custom_art/'))
	print('#'*56)
	asyncio.run(Bot().connect())