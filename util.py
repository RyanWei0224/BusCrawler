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

