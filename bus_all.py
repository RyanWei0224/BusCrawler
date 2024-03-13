import json
import pickle
import os
import re
import time

from collections import defaultdict

CSV_FOLDER = 'csv'
ROUTE_DIR = 'routes'

METHOD_STR = 'method'
LAST_STR = '_last_dict'

ROUTE_CSV = 'route.csv'

HAS_BOTH = False

ROUTE_STR = r'(.*)_(\d{2})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})_line\.json'

WDAY_LIST = [
	'星期一',
	'星期二',
	'星期三',
	'星期四',
	'星期五',
	'星期六',
	'星期日',
]

BUS_LIST = [
	('ZJ_606',	1,	54),	# 2023/6/29
	('ZJ_633',	5,	10),	# 2023/6/29
	('DY_7',	3,	10),	# 2023/4/15
	('DY_15',	8,	20),	# 2023/4/15
	('DY_15Z',	11,	23),	# 2023/4/30
	('DY_208',	9,	38),	# 2023/4/1
	('DY_209',	3,	23),	# 2023/10/31
	('DY_209Z',	3,	30),	# 2023/4/1
	('CZ_34',	1,	39),	# 2023/6/29
	('CZ_B1',	15,	28),	# 2023/7/10
	('CZ_68',	6,	61),	# 2023/8/30
	('WX_26',	2,	41),	# 2023/7/17
	('WX_G1',	5,	11),	# 2023/7/17
	('WX_WT',	4,	32),	# 2023/7/17
	('SZR_SX1',	4,	 7),	# 2023/10/23
	('SZR_85',	1, 26, 43),	# 2023/7/16
	('SZR_158', 2, 34, 39),	# 2023/7/16
	('SZR_KX9', 6, 25, 28),	# 2023/9/18
	('SZR_113',23, 25, 35),	# 2023/7/27
	('KS_C2',	1,	19),	# -
	('KS_126',	1,	23),	# -
	('KS_101',	2,	 3),	# -
	('KS_102',	1, 17, 33), # -
]

FIRST_TIME = '23/10/31'

# 1 for a<b
# -1 for a>b
# 0 for a=b
# None for no relation
def relation_of(info1, info2, n, pr):
	s1 = set(info1.keys())
	s2 = set(info2.keys())
	s = s1 & s2
	n_frac = max(4, 0.2 * n)
	if len(s) < n_frac:
		return None

	l = []
	nlarge = 0
	for k in s:
		nlarge += info2[k] - info1[k]
		if info1[k] < info2[k]:
			l.append(1)
		elif info2[k] < info1[k]:
			l.append(-1)

	s1_large = l.count(-1)
	s2_large = l.count(1)
	thrs_num = 0.4 * len(l)
	max_large = 0
	max_slot = None
	cur_slot = None
	cur_num = 0
	for i in l:
		if cur_slot != i:
			if cur_num > max_large:
				max_large = cur_num
				if max_slot is None and cur_num >= thrs_num:
					max_slot = cur_slot
			cur_slot = i
			cur_num = 0
		cur_num += 1

	if cur_num > max_large:
		max_large = cur_num
		if max_slot is None and cur_num >= thrs_num:
			max_slot = cur_slot

	# assert max_slot is not None
	'''
	if max_slot is not None:
		return max_slot

	return None
	'''

	if abs(nlarge) < 60:
		return None

	if s1_large < n_frac and s2_large < n_frac:
		return None

	if s1_large > 0.25 * (s1_large+s2_large) and s2_large > 0.25 * (s1_large+s2_large):
		return None

	if max_slot is not None:
		return max_slot

	if s1_large < s2_large:
		return 1
	elif s1_large > s2_large:
		return -1

	if nlarge > 0:
		return 1
	elif nlarge < 0:
		return -1

	return 1


def topo_sort(kv_dict, n, pr = False):
	ks = list(kv_dict.keys())
	if len(ks) <= 1:
		return ks
	prevs = [set() for _ in ks]
	nexts = [set() for _ in ks]
	for i, k in enumerate(ks):
		for j in range(i-1):
			last_k = ks[j]
			res = relation_of(kv_dict[last_k], kv_dict[k], n, pr = pr)
			if res is None:
				pass
			elif res == 1:
				# nexts[j].add(i)
				prevs[i].add(j)
			elif res == -1:
				prevs[j].add(i)
				# nexts[i].add(j)
			else:
				assert False

	if pr:
		for i, j in enumerate(prevs):
			print(i, j)

	for i, prev in enumerate(prevs):
		for j in prev:
			nexts[j].add(i)

	nPrevs = [len(i) for i in prevs]
	ready_set = set(i for i in range(len(nPrevs)) if nPrevs[i] == 0)
	res = []
	while ready_set:
		max_idx = min(ready_set)
		ready_set.remove(max_idx)
		res.append(ks[max_idx])
		for i in nexts[max_idx]:
			nPrevs[i] -= 1
			if nPrevs[i] == 0:
				ready_set.add(i)

	if len(res) < len(ks):
		print(f'Less: {len(res)}, {len(ks)}')
		x = [(nPrevs[i], ks[i]) for i in range(len(nPrevs)) if ks[i] not in res]
		x.sort()
		res += [i for _, i in x]


	return res


def get_stations(fname, meth):

	stations = []

	with open(fname, 'r', encoding = 'utf-8') as f:
		data = json.load(f)

	if meth == 0:
		stations = [s['sn'] for s in data['stations']]
	elif meth == 1:
		stations = [s['stationName'] for s in data['stationDetailList']]
	elif meth == 2:
		stations = [s['stationName'] for s in data['data']]
	elif meth == 3:
		stations = [s['Station_Name'] for s in data]
	elif meth == 4:
		stations = [s['stationName'] for s in data['stations']]
	elif meth == 5:
		stations = [s['standName'] for s in data['standInfo']]
	elif meth == 6:
		stations = [s['stationName'] for s in data['station']]
	elif meth == 7:
		stations = [s['sname'] for s in data['list']]
	elif meth == 8:
		stations = [s['stationName'] for s in data['lineStationInfo']]
	elif meth == 9:
		stations = [s['ZDMC'] for s in data['line']]
	elif meth == 10:
		stations = [s['zdmc'] for s in data]
	elif meth == 11:
		stations = [s['stationName'] for s in data]
	else:
		assert False, f'Unknown meth {meth}'

	return stations


def get_route_info(meth_dict):
	route_list = []
	for name in os.listdir(ROUTE_DIR):
		try:
			res = re.fullmatch(ROUTE_STR, name)
			assert res is not None, f'Cannot match "{name}"'
			bus_name = res[1]
			day = f'{res[2]}/{res[3]}/{res[4]}'
			daytime = f'{res[5]}:{res[6]}:{res[7]}' # int(res[5]) * 3600 + int(res[6]) * 60 + int(res[7])
			fname = f'{ROUTE_DIR}/{name}'
			t = time.strptime(name, f'{res[1]}_%y%m%d_%H%M%S_line.json')
			t = time.mktime(t)
			route_list.append((bus_name, t, fname, day, daytime))
		except Exception as e:
			print(name)
			print(e, type(e))
			_ = input()
			continue

	route_list.sort()

	route_dict = defaultdict(list)

	for bus_name, t, fname, day, daytime in route_list:
		if bus_name not in meth_dict:
			# print(f'Cannot find {bus_name}')
			continue
		meth = meth_dict.get(bus_name, 0)
		try:
			stations = get_stations(fname, meth)
		except Exception as e:
			print(f'Cannot decode route {fname}!')
			print(e, type(e))
			_=input()
			continue
		if stations is None:
			continue
		route_dict[bus_name].append((f'{day} {daytime}', stations))
		# route_dict[bus_name].append(f'{day} {daytime},{stations}')

	return route_dict
	

def to_time(t):
	s = t % 60
	t = t // 60
	m = t % 60
	h = t // 60

	def to_str2(x):
		return f'{x}' if x >= 10 else f'0{x}'
	h = to_str2(h)
	m = to_str2(m)
	s = to_str2(s)
	return f'{h}:{m}:{s}'


def post_proc(obus_dict, num_stations):
	for bus, i in obus_dict.items(): # bus
		n = num_stations[bus]
		ks = list(i.keys())
		for key in ks:
			j = i[key] # bus_day
			assert LAST_STR in j
			w = j[LAST_STR]
			del j[LAST_STR]
			for k in w:
				w[k][0] = to_time(w[k][0])
				if w[k][-1] is not None:
					w[k][-1] = to_time(w[k][-1])
			try:
				j_list = topo_sort(j, n, pr = False)
			except Exception as e:
				print(bus, key)
				raise
			i[key] = [(k, sorted([(stop_id, to_time(j[k][stop_id])) for stop_id in j[k]])) for k in j_list]
			i[key].append((LAST_STR, w))


def main():
	with open('all.pickle', 'rb') as f:
		d = pickle.load(f)

	'''
	with open('all.json', 'r', encoding = 'utf-8') as f:
		d = json.load(f)
	'''
	from lines import LINES
	del_keys = [k for k in d if k not in LINES]
	for k in del_keys:
		del d[k]

	meth_dict = {bus_name: d[bus_name].pop(METHOD_STR) for bus_name in d if METHOD_STR in d[bus_name]}

	num_stations = dict()
	for line in d:
		linfo = d[line]
		if HAS_BOTH:
			n = max((k for i in linfo.values() for l, j in i.items() if l != LAST_STR for (k, _), _ in j.items()), default = 0) + 1
		else:
			n = max((k for i in linfo.values() for l, j in i.items() if l != LAST_STR for k, _ in j.items()), default = 0) + 1
		num_stations[line] = n


	post_proc(d, num_stations)
	route_dict = get_route_info(meth_dict)

	for line in d:
		try:
			f = open(f'{CSV_FOLDER}/{line}.csv', 'w', encoding = 'GBK')
		except Exception as e:
			print(f'Cannot open {line}.csv, skipping...')
			continue
		linfo = d[line]
		n = num_stations[line]
		print(f'{line},', end = '', file = f)
		print(*list(range(1, n+1)), sep = ',', end = '', file = f)
		print(',last', file = f)

		last_s = None
		for day_str, stations in route_dict[line]:

			stations = ','.join(stations)
			if stations == last_s:
				continue
			print(f'{day_str},{stations}', file = f)
			last_s = stations

		for day in reversed(linfo):
			dinfo = linfo[day]
			wday = time.strptime(day, '%y/%m/%d').tm_wday
			wday = WDAY_LIST[wday]
			print(f'{day},{wday}', file = f)
			last_info = dinfo.pop()
			assert last_info[0] == LAST_STR
			last_info = last_info[1]
			for car, cinfo in dinfo:
				if len(cinfo) <= 1:
					continue

				assert car in last_info, f'data[{line}][{day}][{LAST_STR}] has no {car}...'

				if HAS_BOTH:
					x = [''] * n
					y = [''] * n
					for i, j in cinfo:
						station_id, bus_stat = i
						if bus_stat == 1:
							z = x
						else:
							assert bus_stat == 0
							z = y
						assert z[station_id] == ''
						z[station_id] = j
					x = [f'{i}-{j}' for i, j in zip(x, y)]
				else:
					x = ['-'] * n
					for i, j in cinfo:
						assert x[i] == '-'
						x[i] = j

				x = [car] + x + [last_info[car][0] + (('-' + last_info[car][-1]) if last_info[car][-1] is not None else '')]
				print(*x, sep = ',', file = f)
		f.close()

	'''
	with open(ROUTE_CSV, 'w', encoding = 'GBK') as f:
		line1 = ''
		line2 = ''
		s = None
		for line_info in BUS_LIST:
			line = line_info[0]
			line_info = [i-1 for i in line_info[1:]]
			line1 += f',{line}' + ',' * (len(line_info)-1)
			if route_dict[line]:
				route = route_dict[line][-1][-1]
				line2 += f',' + ','.join((route[i] for i in line_info))
			else:
				line2 += ',' * len(line_info)
			linfo = d[line]
			if s is None:
				s = set(linfo.keys())
			else:
				s = s & set(linfo.keys())
		# print(s)
		s = [i for i in s if i >= FIRST_TIME]
		s.sort()
		s.reverse()
		for date in s:
			print(date + line1, line2, sep = '\n', file = f)
			dd = [] # [[] for _ in BUS_LIST] + [[] for _ in BUS_LIST]
			for line_info in BUS_LIST:
				line = line_info[0]
				line_info = [i-1 for i in line_info[1:]]
				assert not HAS_BOTH
				cur_dd = [[] for _ in line_info]
				for _, cinfo in d[line][date]:
					names = ['' for _ in line_info]
					minus = ['' for _ in line_info]
					plus  = ['' for _ in line_info]
					for k, v in cinfo:
						for i, j in enumerate(line_info):
							if k == j:
								names[i] = v
							if k == j-1:
								minus[i] = v
							if k == j+1:
								plus[i] = v
					for i in range(len(names)):
						if not names[i]:
							names[i] = f'{minus[i]}-{plus[i]}'
						cur_dd[i].append(names[i])
				dd += cur_dd

			# print(date + (',' * len(dd)), file = f)
			n = max(len(i) for i in dd)
			for i in range(n):
				cur_str = ''
				for w in dd:
					cur_str += ','
					if len(w) > i:
						cur_str += w[i]
					else:
						cur_str += '#####'
				print(cur_str, file = f)
	'''

if __name__ == '__main__':
	try:
		main()
	except Exception as e:
		print(f'Caught exception {e}')
		raise
	finally:
		_=input('Done...')