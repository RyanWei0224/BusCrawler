import os
import re
import json
import pickle
import shutil

JSON_DIR = 'json'
ROUTE_DIR = 'routes'
OLD_JSON_DIR = 'old_json'

METHOD_STR = 'method'
LAST_STR = '_last_dict'

HAS_BOTH = False

HOURS = 2 * 24

BAD_STAT = (-4, -1)

ROUTE_METHODS = [
	''
]

# 13, 0 : 13 -> 14
# 13, 1 : at 13

def chelaile(bus_data, station_data):
	# 1, 2, 3, ...
	# 13, 0 : 12 -> 13
	# 13, 1 : at 13
	return (bus_data['busId'], int(bus_data['order']) - (1-int(bus_data['state'])) - 1, int(bus_data['state']))

def danyang(bus_data, station_data):
	# 0, 1, 2, ...
	# 13, 2 : 13 -> 14
	# 13, 1 : at 13
	if 'stationId' not in bus_data:
		return (-1,) + BAD_STAT
	station_id = bus_data['stationId']
	return (bus_data['busId'], station_data.index(station_id), 2-int(bus_data['busStatus']))

def zhangshang(bus_data, station_data):
	# 0, 1, 2, ...
	# x, dist_to_x
	station_id = bus_data['index']
	arrive = 1 if bus_data['busToStationNiheDistance'] <= 10.00 else 0
	station_id -= (1-arrive)
	return (bus_data['busNumber'], station_id, arrive)

def changzhou(bus_data, station_data):
	return (bus_data['BusId'], bus_data['Current_Station_Sort'] - 1, bus_data['IsArrive'])

def wuxi(bus_data, station_data):
	arrive = 2 - bus_data['inoutType']
	return (bus_data['busNo'], bus_data['arriveStationNo'] - 1, arrive)

def suzhou(bus_data, station_data):
	# Non-stop
	station_id = bus_data['_stop']
	if station_id in station_data:
		station_id = station_data.index(station_id)
	elif station_id == 'b50cf4ee-f3e1-498f-abce-547eedca6d90':
		station_id = 0
	elif station_id == '71a2d770-7fed-4744-afad-24090ccc18dd' and station_data.count(None) == 1:
		station_id = station_data.index(None)
	elif station_id == '11e58807-dcd7-4b07-81cd-ba00430bed21' and station_data.count(None) == 1:
		station_id = station_data.index(None)
	else:
		raise ValueError(f'"{station_id}" not in station_data')
	bus_id = bus_data['busInfo']
	if isinstance(bus_id, list):
		assert not bus_id, f'List of busInfo must be empty!'
		return (-1,) + BAD_STAT
	return (bus_id, station_id, 0)

def kunshan(bus_data, station_data):
	# 1, 2, 3, ...
	# 13, 0 : 12 -> 13
	# 13, 1 : at 13
	arrive = bus_data['inStation']
	return (bus_data['veh'], bus_data['nextStationNum'] - (1-arrive) - 1, arrive)

def changshu(bus_data, station_data):
	# 1, 2, 3, ...
	arrive = 1
	return (bus_data['dbuscard'], bus_data['slno'] - 1, arrive)

def zhangjiagang(bus_data, station_data):
	# 1, 2, 3, ...
	# 12, 0(1) : at 12
	# 12, 2 : 12 -> 13
	assert bus_data['inoutFlag'] in [0, 1, 2], f'bus_data["inoutFlag"] is {bus_data["inoutFlag"]}'
	arrive = 1 if bus_data['inoutFlag'] != 2 else 0
	return (bus_data['carNo'], bus_data['sortNum'] - 1, arrive)

def jiading(bus_data, station_data):
	# 0, 1, ..., N-1
	# 1, 1: at N-2
	# 1, 0: N-2 -> N-1
	rem_stop = int(bus_data['stopdis'])
	cur_stop = (station_data - 1) - rem_stop
	return (bus_data['terminal'], cur_stop, int(bus_data['inout']))

def shanghai(bus_data, station_data):
	# 0, 1, ..., N-1
	# 1, 1: at N-2
	# 1, 0: N-2 -> N-1
	rem_stop = int(bus_data['stopdis'])
	cur_stop = (station_data - 1) - rem_stop
	return (bus_data['terminal'], cur_stop, 1)

def taicang(bus_data, station_data):
	in_station = 1 - bus_data['inoutType']
	if in_station != 0:
		print(f'In station {1 - in_station}')
		in_station = 1
	return (bus_data['busName'], bus_data['arriveStationNo'] - 1, in_station)



def proc(cur_dict, bus_datas, station_data, daytime, f):
	cur_ids = set()
	for bus_data in bus_datas:
		bus_id, station_id, bus_stat = f(bus_data, station_data)
		if station_id >= 0 and bus_stat in (0, 1):
			pass
		elif (station_id, bus_stat) == BAD_STAT:
			# WT wrong state?
			continue
		else:
			assert False, f'Illegal state ({station_id}, {bus_stat})'

		if bus_id not in cur_dict:
			cur_dict[bus_id] = dict()

		if HAS_BOTH:
			station_id = (station_id, bus_stat)

		if station_id not in cur_dict[bus_id]:
			cur_dict[bus_id][station_id] = daytime
		else:
			assert cur_dict[bus_id][station_id] <= daytime, f'Time is decreasing... {cur_dict[bus_id][station_id]} > {daytime}'
			#cur_dict[bus_id][station_id] = daytime

		if bus_id in cur_dict[LAST_STR]:
			assert cur_dict[LAST_STR][bus_id][0] <= daytime, f'Last time is decreasing... {cur_dict[LAST_STR][bus_id][0]} > {daytime}'
			assert cur_dict[LAST_STR][bus_id][-1] is None or cur_dict[LAST_STR][bus_id][-1] <= daytime, f'Last dissappear time is decreasing... {cur_dict[LAST_STR][bus_id][-1]} > {daytime}'

		cur_dict[LAST_STR][bus_id] = [daytime, None]

		cur_ids.add(bus_id)

	for bus_id in cur_dict[LAST_STR]:
		if bus_id in cur_ids:
			continue
		if cur_dict[LAST_STR][bus_id][-1] is not None:
			continue
		cur_dict[LAST_STR][bus_id][-1] = daytime


REG_STR = r'(.*)_(\d{2})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})\.json'

from collections import defaultdict
import time

def dict_del(d, k):
	if k in d:
		del d[k]

def get_route(name):
	data = None
	maxt = -1
	for i in os.listdir(ROUTE_DIR):
		try:
			t = time.strptime(i, f'{name}_%y%m%d_%H%M%S_line.json')
		except ValueError:
			continue
		t = time.mktime(t)
		if t <= maxt:
			continue
		maxt = t
		data = f'{ROUTE_DIR}/{i}'
		
	if data is None:
		return None

	with open(data, 'r', encoding = 'utf-8') as f:
		data = json.load(f)
	return data

def proc_all(remove_route):

	json_list = []
	all_set = set()
	wrong_set = set()
	new_route = defaultdict(list)

	for name in os.listdir(JSON_DIR):
		try:
			res = re.fullmatch(REG_STR, name)
			assert res is not None, f'Cannot match "{name}"'
			bus_name = res[1]
			day = f'{res[2]}/{res[3]}/{res[4]}'
			daytime = int(res[5]) * 3600 + int(res[6]) * 60 + int(res[7])
			fname = f'{JSON_DIR}/{name}'
			t = time.strptime(name, f'{res[1]}_%y%m%d_%H%M%S.json')
			t = time.mktime(t)
			json_list.append((bus_name, t, fname, day, daytime))
			all_set.add(bus_name)
		except Exception as e:
			print(name)
			print(e, type(e))
			_ = input()
			continue

	glb_dict = defaultdict(lambda: defaultdict(dict))

	'''
	if os.path.isfile('all.json'):
		with open('all.json', 'r', encoding = 'utf-8') as f:
			x = json.load(f)
			glb_dict.update(x)
	'''

	if os.path.isfile('all.pickle'):
		with open('all.pickle', 'rb') as f:
			x = pickle.load(f)
			glb_dict.update(x)

	json_list.sort()

	print(f'Identified {len(json_list)} files')

	if not os.path.isdir(ROUTE_DIR):
		os.mkdir(ROUTE_DIR)

	cur_bus = None
	old_data = None

	del_list = []
	finish_list = []

	for bus_name, t, fname, day, daytime in json_list:
		try:
			if cur_bus != bus_name:
				cur_bus = bus_name
				old_data = get_route(bus_name)
				#print(bus_name, bool(old_data))

			cur_dict = glb_dict[bus_name][day]
			if LAST_STR not in cur_dict:
				cur_dict[LAST_STR] = dict()
			bus_datas = None
			station_data = None
			func = None

			with open(fname, 'r', encoding = 'utf-8') as f:
				data = json.load(f)

			meth = data['_meth']

			if METHOD_STR not in glb_dict[bus_name]:
				glb_dict[bus_name][METHOD_STR] = meth
			else:
				assert(glb_dict[bus_name][METHOD_STR] == meth)

			if meth == 0:
				func = chelaile

				data = data['jsonr']

				#if (not data['success']) or data['status'] != '00':
				if not data['success']:
					assert False, f'Failed! success: {data["success"]}, status: {data["status"]}, msg: {data.get("errmsg", "")}'

				data = data['data']
				bus_datas = data['buses']
				del data['buses']

				dict_del(data, 'tip')
				dict_del(data, 'depDesc')
				dict_del(data, 'depTable')
				dict_del(data['line'], 'desc')
				dict_del(data['line'], 'ksDesc')
				dict_del(data['line'], 'shortDesc')
				dict_del(data['line'], 'state')
				dict_del(data['line'], 'assistDesc')
				dict_del(data['line'], 'nextOperationTimeDesc')
				dict_del(data['line'], 'ksAssistDesc')
				dict_del(data['line'], 'lineDisplayTags')
				dict_del(data['line'], 'lineDisplayTags')
				dict_del(data, 'roads')
				dict_del(data, 'preArrivalTime')
				dict_del(data, 'predictionLink')
				dict_del(data, 'predictionText')
				dict_del(data, 'nearStnOrder')
				dict_del(data, 'targetOrder')
				'''
				for i in data['roads']:
					for j in i:
						#dict_del(j, 'TPC')
						dict_del(j, 'TVL')
				'''
			elif meth == 1:
				func = danyang

				#if data['code'] != 200 or data['msg'] != '成功':
				if data['code'] != 200 and data['msg'] != '成功':
					assert False, f'Failed! code: {data["code"]}, msg: {data["msg"]}'

				data = data['data']
				bus_datas = data['busList']
				del data['busList']

				station_data = data['stationDetailList']
				station_data = [station['stationId'] for station in station_data]
			elif meth == 2:
				func = zhangshang

				if data['status'] != 1 and data['msg'] != '获取实时数据成功!':
					assert False, f'Failed! status: {data["status"]}, msg: {data["msg"]}'

				bus_datas = data['list']
				data = None
			elif meth == 3:
				func = changzhou

				if data['resCode'] != 10000 and data['resMsg'] != '成功':
					assert False, f'Failed! resCode: {data["resCode"]}, resMsg: {data["resMsg"]}'

				bus_datas = data['value']
				data = None
			elif meth == 4:
				func = wuxi

				if data['result'] == '2' and data['message'] == 'token无效或者已过期':
					del_list.append(fname)
					continue

				if data['result'] != '0' and data['message'] != 'success':
					assert False, f'Failed! result: {data["result"]}, message: {data["message"]}'

				bus_datas = data['items']

				data = None
				'''
				data = data['_line']

				if data is not None:
					if data['result'] != '0' and data['message'] != 'success':
						assert False, f'Failed! (Line) result: {data["result"]}, message: {data["message"]}'

					data = data['items']
				'''
			elif meth == 5:
				func = suzhou

				if data['code'] == '100501' and data['msg'] == '请求失败':
					del_list.append(fname)
					continue

				if data['code'] != '0' and data['msg'] != '':
					assert False, f'Failed! code: {data["code"]}, msg: {data["msg"]}'

				bus_datas = []
				if 'standInfo' in data['data']:
					if isinstance(data['data']['standInfo'], list):
						assert not data['data']['standInfo'], f'List of standInfo must be empty!'
					else:
						for k, vs in data['data']['standInfo'].items():
							for v in vs:
								v = v.copy()
								v['_stop'] = k
								bus_datas.append(v)

				data = data['_line']

				if data['code'] != '0' and data['msg'] != '':
					assert False, f'Failed! (Line) code: {data["code"]}, msg: {data["msg"]}'

				data = data['data']
				station_data = [i['standSguid'] for i in data['standInfo']]
			elif meth == 6:
				func = kunshan

				if data['code'] != 0:
					assert False, f'Failed! code: {data["code"]}'

				bus_datas = data['data']['vehPosiList']
				data = None
			elif meth == 7:
				func = changshu
				if data['type'] != 'response' or data['status'] != '200':
					assert False, f'Failed! type: {data["type"]}, status: {data["status"]}'

				bus_datas = data['content']
				data = None
			elif meth == 8:
				func = zhangjiagang
				if data['code'] != 0 or data['ok'] != True:
					assert False, f'Failed! code: {data["code"]}, ok: {data["ok"]}'

				data = data['data']
				bus_datas = data['busInfo']
				data = {
					i : data[i] for i in ['line', 'lineStationInfo', 'lintTime']
				}
				del data['line']['updateTime']
				for i in data['lineStationInfo']:
					del i['updateTime']
				for i in data['lintTime']:
					del i['updateTime']
					del i['createTime']
					del i['id']
			elif meth == 9:
				func = jiading
				bus_datas = data['data']
				data = data['_line']
				station_data = len(data['line'])

				for i in data['sch']:
					dict_del(i, 'id')
					dict_del(i, 'scheduleDateStr')
					dict_del(i, 'nbbm')
					dict_del(i, 'jsy')
			elif meth == 10:
				func = shanghai
				if data['code'] != '200' or data['desc'] != '操作成功':
					assert False, f'Failed! code: {data["code"]}, desc: {data["desc"]}'

				bus_datas = data['data']
				if isinstance(bus_datas, str):
					bus_datas = []
				else:
					bus_datas = bus_datas['cars']['car']

				data = data['_line']
				station_data = len(data)
			elif meth == 11:
				func = taicang

				bus_datas = data['items']
				data = None
			else:
				assert False, f'Unknown meth {meth}'

			if data != old_data and data is not None:
				dname = fname.replace('.json', '_line.json')
				dname = dname.replace(JSON_DIR+'/', ROUTE_DIR+'/')
				old_data = data
				assert not os.path.isfile(dname)
				assert dname not in new_route[bus_name]
				new_route[bus_name].append(dname)
				with open(dname, 'w', encoding = 'utf-8') as f:
					json.dump(data, f, ensure_ascii = False, indent = '\t')
				print('New route info:', dname)

			proc(cur_dict, bus_datas, station_data, daytime, func)
		except Exception as e:
			print(fname)
			print(e, type(e))
			wrong_set.add(bus_name)
			#_ = input()
			continue
			# return glb_dict
		else:
			finish_list.append((bus_name, fname))

	for fname in del_list:
		print(f'Delete {fname}')
		os.remove(fname)

	if wrong_set:
		for bus_name in new_route:
			if not (remove_route or bus_name in wrong_set):
				continue
			for dname in new_route[bus_name]:
				if os.path.isfile(dname):
					os.remove(dname)

	if not os.path.isdir(OLD_JSON_DIR):
		os.mkdir(OLD_JSON_DIR)

	assert all(i in all_set for i in wrong_set)
	all_wrong = (len(all_set) == len(wrong_set) and all_set)

	return glb_dict, finish_list, wrong_set, all_wrong

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

'''
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
'''

def main(per_bus = True):
	glb_dict, finish_list, wrong_set, all_wrong = proc_all(remove_route = not per_bus)
	if all_wrong or (wrong_set and not per_bus):
		return None

	# post_proc(glb_dict)
	'''
	with open('all.json', 'w', encoding = 'utf-8') as f:
		json.dump(glb_dict, f, ensure_ascii = False, indent = '\t')
	'''

	shutil.copy2('all.pickle', 'all_bak.pickle')
	with open('all.pickle', 'wb') as f:
		gd = dict()
		gd.update(glb_dict)
		pickle.dump(gd, f)
	
	minTime = time.time() - HOURS * 3600

	for name in os.listdir(OLD_JSON_DIR):
		fname = f'{OLD_JSON_DIR}/{name}'
		if os.stat(fname).st_mtime <= minTime :
			os.remove(fname)

	for bus_name, fname in finish_list:
		if bus_name in wrong_set:
			continue
		if os.stat(fname).st_mtime <= minTime:
			os.remove(fname)
			continue
		new_name = fname.replace(JSON_DIR+'/', OLD_JSON_DIR+'/')
		os.rename(fname, new_name)

	return (not wrong_set)


if __name__ == '__main__':
	main()
	_=input('Done...')
