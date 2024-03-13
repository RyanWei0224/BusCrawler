import time
from mail import send_mail

TPOINT_STR = '_timep'

PICKLE_DIR = 'pickle'
PICBAK_DIR = 'pickle_bak'
ROUTE_DIR = 'routes'

LOG_FILE = 'bus.log'


from functools import total_ordering
@total_ordering
class CT():
	def __init__(self, h, m):
		self.t = h * 60 + m

	def __int__(self):
		return self.t

	def __eq__(self, other):
		return self.t == other.t

	def __lt__(self, other):
		return self.t < other.t


def cur_time():
	x = time.localtime()
	return CT(x.tm_hour, x.tm_min)


def init():
	import os
	for d in (PICKLE_DIR, PICBAK_DIR, ROUTE_DIR):
		os.makedirs(d, exist_ok=True)


def merge_dict(d1, d2, max_depth = -1):
	d = dict()
	ks = set(d1.keys()) | set(d2.keys())
	for k in ks:
		if k not in d1:
			assert k in d2, 'Logic Error!'
			d[k] = d2[k]
			continue

		if k not in d2:
			assert k in d1, 'Logic Error!'
			d[k] = d1[k]
			continue

		if max_depth == 0:
			assert False, 'Detected merge at max depth!'

		if isinstance(d1[k], dict):
			assert isinstance(d2[k], dict), f'Type mismatch: {type(d1[k])} v.s. {type(d2[k])}'
			d[k] = merge_dict(d1[k], d2[k], max_depth = max_depth - 1)
			continue

		if isinstance(d1[k], list):
			assert isinstance(d2[k], list), f'Type mismatch: {type(d1[k])} v.s. {type(d2[k])}'
			d[k] = d1[k] + d2[k]
			continue

		assert False, f'Unrecognized type for d: {type(d1[k])}'

	return d


def dict_empty(d):
	for v in d.values():
		assert isinstance(v, dict) or isinstance(v, list), f'Unrecognized type {type(v)}'
		if isinstance(v, dict) and not dict_empty(v):
			return False
		if isinstance(v, list) and v:
			return False

	return True


def dict_del(d, k):
	if k in d:
		del d[k]


def sleep_intr(t, stop_l):
	t += time.time()
	while time.time() + 1.5 < t:
		if stop_l:
			return
		time.sleep(1)

	if stop_l:
		return
	t -= time.time()
	if t > 0:
		time.sleep(t)


def print_log(*args, verbose = False, **kwargs):
	with open(LOG_FILE, 'a', encoding = 'utf-8') as f:
		print(f'[{time.strftime("%m/%d %X")}]', *args, file = f, **kwargs)
	if verbose:
		print(f'[{time.strftime("%m/%d %X")}]', *args, **kwargs)


LINE_JSON_FMT =  '{lname}_%y%m%d_%H%M%S_line.json'
LINE_JSON_RE  = r'(.*)_\d{6}_\d{6}_line\.json'


def ljson_name(line_name, t):
	return time.strftime(f'{ROUTE_DIR}/{LINE_JSON_FMT.format(lname = line_name)}', t)


def ljson_files(line_name):
	import os
	files = []
	for fname in os.listdir(ROUTE_DIR):
		try:
			t = time.strptime(fname, LINE_JSON_FMT.format(lname = line_name))
		except ValueError:
			continue
		t = time.mktime(t)
		fname = f'{ROUTE_DIR}/{fname}'
		files.append((t, fname))
	return files


def ljson_lastf(line_name):
	files = ljson_files(line_name)
	return max(files, default = (-1, None))


def ljson_allfs():
	import os, re
	files = dict()
	for fname in os.listdir(ROUTE_DIR):
		res = re.fullmatch(LINE_JSON_RE, fname)
		if res is None:
			continue
		line_name = res[1]
		try:
			t = time.strptime(fname, LINE_JSON_FMT.format(lname = line_name))
		except ValueError:
			continue
		t = time.mktime(t)
		fname = f'{ROUTE_DIR}/{fname}'
		if line_name not in files:
			files[line_name] = []
		files[line_name].append((t, fname))
	return files

