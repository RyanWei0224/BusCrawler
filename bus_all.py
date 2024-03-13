
import json
import pickle

CSV_FOLDER = 'csv'

LAST_STR = '_last_dict'

HAS_BOTH = False


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


def post_proc(obus_dict):
	for i in obus_dict.values(): # bus
		for j in i.values(): # bus_day
			assert LAST_STR in j
			for k in j[LAST_STR]:
				j[LAST_STR][k][0] = to_time(j[LAST_STR][k][0])
				if j[LAST_STR][k][-1] is not None:
					j[LAST_STR][k][-1] = to_time(j[LAST_STR][k][-1])
			for k in j: # bus_day_id
				if k == LAST_STR:
					continue
				j[k] = sorted([(stop_id, to_time(j[k][stop_id])) for stop_id in j[k]])

with open('all.pickle', 'rb') as f:
	d = pickle.load(f)

'''
with open('all.json', 'r', encoding = 'utf-8') as f:
	d = json.load(f)
'''

post_proc(d)

for line in d:
	f = open(f'{CSV_FOLDER}/{line}.csv', 'w', encoding = 'utf-8')
	linfo = d[line]
	if HAS_BOTH:
		n = max((k for i in linfo.values() for l, j in i.items() if l != LAST_STR for (k, _), _ in j), default = 0) + 1
	else:
		n = max((k for i in linfo.values() for l, j in i.items() if l != LAST_STR for k, _ in j), default = 0) + 1
	print(f'{line},', end = '', file = f)
	print(*list(range(1, n+1)), sep = ',', end = '', file = f)
	print(',last', file = f)
	for day in linfo:
		dinfo = linfo[day]
		print(day, file = f)
		last_info = dinfo[LAST_STR]
		del dinfo[LAST_STR]
		for car in dinfo:
			cinfo = dinfo[car]
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

_=input('Done...')
