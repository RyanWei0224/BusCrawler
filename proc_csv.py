import os
import time
from collections import defaultdict

from util import CSV_DIR, PICKLE_DIR, DATE_FORMAT, TPOINT_STR, ljson_files
from util import load_json, load_pkl

WDAY_LIST = [
	'星期一',
	'星期二',
	'星期三',
	'星期四',
	'星期五',
	'星期六',
	'星期日',
]


def proc_csv(lines = None):
	if lines is None:
		assert False, 'TODO! Not implemented yet.'

	for route_name in lines:
		fname = f'{PICKLE_DIR}/{route_name}.pickle'
		if not os.path.isfile(fname):
			print(f'[Warning] {route_name} not found!')
			continue

		res = load_pkl(fname)

		meth = lines[route_name][-1]
		proc_route(route_name, meth, res)


def proc_route(route_name, meth, res):
	stop_info = get_route_stops(route_name, meth)

	days = sorted(res.keys(), reverse = True)

	max_sid = -1
	res_list = []
	for day in days:
		day_res = proc_day(res[day])
		res_list.append((day, day_res))
		cur_sid = max((max((ts for ts in bus_info.keys()), default = -1) for _, bus_info, _ in day_res), default = -1)
		max_sid = max(max_sid, cur_sid)
	num_sid = max_sid + 1

	try:
		f = open(f'{CSV_DIR}/{route_name}.csv', 'w', encoding = 'GBK')
	except Exception:
		print(f'Cannot open {route_name}.csv, skipping...')
		return

	cur_row = [route_name]
	cur_row += range(1, num_sid + 1)
	if num_sid > 0:
		cur_row.append('last')
	print(*cur_row, sep = ',', file = f)

	last_stops = None
	for day, stops in stop_info:
		stops = ','.join(stops)
		if stops == last_stops:
			continue
		last_stops = stops

		cur_row = [day, stops] if stops else [day]
		print(*cur_row, sep = ',', file = f)


	for day, day_res in res_list:
		wday = time.strptime(day, DATE_FORMAT).tm_wday
		wday = WDAY_LIST[wday]
		print(f'{day},{wday}', file = f)

		for bus, stop_dict, last_info in day_res:
			cur_row = ['-'] * num_sid

			def _proc(t):
				t, s = divmod(t, 60)
				h, m = divmod(t, 60)
				return f'{h:02d}:{m:02d}:{s:02d}'

			for stop, ts in stop_dict.items():
				cur_row[stop] = ' '.join(_proc(t) for t in ts)

			cur_row = [bus] + cur_row
			if last_info[-1] is None:
				cur_row.append(_proc(last_info[0]))
			else:
				cur_row.append(_proc(last_info[0]) + '-' + _proc(last_info[-1]))

			print(*cur_row, sep = ',', file = f)

	f.close()
	return


# Return [(day, [stop1, stop2, ...]), ...]
def get_route_stops(route_name, meth):
	from crawlers.all import ALL_CRAWLERS
	crawler = ALL_CRAWLERS[meth]
	line_files = ljson_files(route_name)
	stop_info = []
	for t, fname in line_files:
		line_json = load_json(fname)
		t = time.localtime(t)
		t = time.strftime('%y/%m/%d %X', t)
		stations = crawler.get_stations(line_json)
		stations = [i[0] for i in stations]
		stop_info.append((t, stations))
	return stop_info


# Input {TPOINT_STR: [t1, ...], bus1: [(t1, s1, ...), ...], bus2: [...]}
# Return [(bus, {stop: [t1, t2, ...]}, last), ...]
def proc_day(res_day):
	if not res_day:
		return []
	assert TPOINT_STR in res_day, 'res_day has not TPOINT_STR!'
	tps = res_day[TPOINT_STR]
	tps.sort()

	buses = []
	for bus, l in res_day.items():
		if bus == TPOINT_STR:
			continue

		if not l:
			continue
		l.sort()

		stop_info = defaultdict(list)
		last_stop = None
		for sinfo in l:
			t, sid = sinfo[:2]
			if last_stop == sid:
				continue
			last_stop = sid
			stop_info[sid].append(t)
		stop_info = dict(stop_info)

		last_t = l[-1][0]
		import bisect
		next_idx = bisect.bisect_right(tps, last_t)
		if next_idx >= len(tps):
			next_t = None
		else:
			next_t = tps[next_idx]

		buses.append((bus, stop_info, (last_t, next_t)))

	return buses


def main():
	from lines import LINES
	proc_csv(lines = LINES)


if __name__ == '__main__':
	try:
		main()
	except Exception as e:
		print(f'Caught exception {e}')
		raise
	finally:
		_=input('Done...')

