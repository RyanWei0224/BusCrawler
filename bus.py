import json
import time
import requests
import threading
import os
from lxml import etree

from mail import send_mail
from read_bus import main as read_bus
from bus_all import main as bus_all

INTV = 19
PING_INTV = 60


from crawlers.all import ALL_CRAWLERS
from util import sleep_intr, print_log, CT


def cur_time():
	x = time.localtime()
	return CT(x.tm_hour, x.tm_min)

def cur_date():
	x = time.localtime()
	return x.tm_mday

def upd_wuxi_token(data):
	global WX_HEADERS
	if data['result'] != '2' or data['message'] != 'token无效或者已过期':
		return None
	try:
		x = requests.post(WX_TOK_URL, json = WX_TOK_JSON)
		x.raise_for_status()
		new_token = x.json()['items']['token']
		WX_HEADERS['token'] = new_token
	except Exception as e:
		print(e)
		send_mail(f'Error: {e} while loading wuxi')
		time.sleep(180)
		raise
		# return False
	return True




def get_req_new(crawler, endt = None, stop_l = [], get_line = False, update = True):
	tries = 0
	intv = 3
	timeout = 3.05
	while not (stop_l or (endt is not None and cur_time() >= endt)):
		try:
			# t = time.time()
			tries += 1
			res_json, get_t = crawler.get_once(get_line = get_line, timeout = timeout)
		except Exception as e:
			if crawler.stop():
				raise e

			err_str = f'Error "{e}" at {crawler.name()}'
			if get_line:
				print(err_str)
			print_log(err_str)

			if '429 Client Error: Too Many Requests' in str(e):
				sleep_intr(30, stop_l)
				continue

			if tries in (3, 6):
				timeout += 3.05

			'''
			t = (t + intv) - time.time()
			if t > 0:
				sleep_intr(t, stop_l)
			'''
			sleep_intr(intv, stop_l)

			if intv < 20 and tries >= 3:
				intv += 2

			continue

		if res_json is None or not update:
			break

		try:
			crawler.proc_update(res_json, get_t)
		except Exception as e:
			print(f'Exception at proc: {e}')

		break

	return


def line_thread_new(crawler, endt, stop_l, update = True):
	try:
		while (cur_time() < endt or endt is None) and not stop_l:
			t0 = time.time()
			t = t0 + INTV
			try:
				get_req_new(crawler, endt = endt, stop_l = stop_l, update = update)
			except Exception as e:
				print(f'At line {crawler.name()}: {e} of {type(e)}')
				return
			t0 = time.time() - t0
			print_log(f'Delay: {t0}s. {crawler.name()}')
			t = t - time.time()
			if t > 0:
				sleep_intr(t, stop_l)
	except KeyboardInterrupt:
		return

'''
fname = time.strftime(f'{JSON_DIR}/{name}_%y%m%d_%H%M%S.json', get_t)
			with open(fname, 'w', encoding='utf-8') as f:
				json.dump(res, f, ensure_ascii = False, indent = '\t')
'''

from read_bus import get_route, ROUTE_DIR
def update_route(bus_name, data, get_t):
	old_data = get_route(bus_name)
	if data != old_data and data is not None:
		dname = time.strftime(f'{ROUTE_DIR}/{bus_name}_%y%m%d_%H%M%S_line.json', get_t)
		assert not os.path.isfile(dname)
		with open(dname, 'w', encoding = 'utf-8') as f:
			json.dump(data, f, ensure_ascii = False, indent = '\t')
		print('New route info:', dname)

def get_routes(lines):
	# 2, 3, 4, 6, 7
	for name, line in lines.items():
		meth = line[-1]
		line_info = line[0]
		if meth not in [2, 3, 4, 6, 7, 11]:
			continue

		try:
			url = get_url(line_info, meth)
			data, get_t = get_req(url, meth = meth, get_line = True)
			if meth == 2:
				if data['status'] != 1 and data['msg'] != '获取实时数据成功!':
					assert False, f'Failed! status: {data["status"]}, msg: {data["msg"]}'
				del data['_meth']
			elif meth == 3:
				if data['resCode'] != 10000 and data['resMsg'] != '成功':
					assert False, f'Failed! resCode: {data["resCode"]}, resMsg: {data["resMsg"]}'
				data = data['value']
			elif meth == 4:
				if data['result'] != '0' and data['message'] != 'success':
					assert False, f'Failed! result: {data["result"]}, message: {data["message"]}'
				data = data['items']
				segId = line_info[-1]
				for d in data:
					if str(d['segmentId']) == str(segId):
						data = d
						break
				else:
					assert False, f'Cannot find segment {segId}'
			elif meth == 6:
				if data['code'] != 0:
					assert False, f'Failed! code: {data["code"]}'
				data = data['data']
				upDown = line_info[-1]
				data['station'] = data['stationListUp'] if upDown == 0 else data['stationListDown']
				del data['stationListUp']
				del data['stationListDown']
			elif meth == 7:
				if data['msg'] != '数据取得成功！' or data['succ'] is not True:
					assert False, f'Failed! msg: {data["msg"]}, succ: {data["succ"]}'

				data = data['dataObj']
				for d in data['list']:
					del d['lbguid']
			else:
				assert False

			update_route(name, data, get_t)
		except Exception as e:
			print(type(e), e, name, "at get_routes")
			continue


def upd_routes(lines):
	print('Update routes...')
	get_routes(lines)
	print('Finished')


def ping_thread(lines, stop_l):
	'''
	def ping_thr(name, url, meth, stop_l):
		t = time.time()
		while not stop_l:
			t += PING_INTV
			t0 = time.time()
			try:
				res, get_t = get_req(url, meth = meth, stop_l = stop_l)
			except Exception as e:
				print_log(f'PING ERROR: {type(e)} {e} {name}')
				print(f'PING ERROR: {type(e)} {e} {name}')
				return
			t0 = time.time() - t0
			print_log(f'[{time.strftime("%m/%d %X")}] Delay: {t0}s. {name}')
			x = t - time.time()
			if x > 0:
				sleep_intr(x, stop_l)
			t = time.time()

	lines = {k:(get_url(v[0], v[-1]), v[-1]) for k, v in lines.items()}
	thrs = [threading.Thread(target = ping_thr, args = (name, url, meth, stop_l)) for name, (url, meth) in lines.items()]
	'''

	thrs = [threading.Thread(target = line_thread_new,
				args = (ALL_CRAWLERS[v[-1]](k, v[0]), None, stop_l), kwargs = {'update': False})
			for k, v in lines.items()]

	for i in thrs:
		i.start()
	for i in thrs:
		i.join()
	return

def check_lines(l):
	def proc(v):
		if not isinstance(v, (list, dict)):
			return v
		assert not isinstance(v, dict)
		v = tuple(proc(i) for i in v)
		return v

	urls = dict()
	for name in l:
		if name == 'SZR_106M_2':
			continue
		var = l[name]
		url = (proc(var[0]), var[-1])
		if url in urls:
			print(f'Find same route! {urls[url]} = {name}')
			return False
		urls[url] = name
	return True


def main_new(l, pl):
	assert check_lines(l)

	from util import init
	init()

	stop_l = []
	running = dict()

	try:
		ping_thr = threading.Thread(target = ping_thread, args = (pl, stop_l))
		ping_thr.start()

		while True:
			time.sleep(1)
			ct = cur_time()
			if ct < CT(1, 0):
				for i in range(len(email_sent)):
					email_sent[i] = False

				for i in running.values():
					i.join()
				running.clear()

			for bus_name in l.keys():
				line_info, startt, endt, meth = l[bus_name]
				if bus_name not in running and startt <= ct and ct < endt:
					crawler = ALL_CRAWLERS[meth](bus_name, line_info)
					thr = threading.Thread(target = line_thread_new, args = (crawler, endt, stop_l))
					running[bus_name] = thr
					thr.start()
					time.sleep(2)

	except KeyboardInterrupt:
		print('Ctrl-C detected. Stopping...')
		pass

	stop_l.append(True)
	for i in running:
		running[i].join()
	ping_thr.join()

def main(l, pl):
	global email_sent
	running = dict()
	stop_l = []

	assert check_lines(l)

	if not os.path.isdir(JSON_DIR):
		os.mkdir(JSON_DIR)

	last_d = cur_date()

	try:

		ping_thr = threading.Thread(target = ping_thread, args = (pl, stop_l))
		ping_thr.start()

		# upd_routes(l)

		while True:
			time.sleep(1)
			ct = cur_time()
			if ct < CT(1, 0):
				for i in range(len(email_sent)):
					email_sent[i] = False
				if running:
					for i in running:
						running[i].join()
					running = dict()
					upd_routes(l)
				cur_d = cur_date()
				if last_d != cur_d:
					ret = read_bus(per_bus = False)
					if ret is None or not ret:
						send_mail('Read bus error...')
					else:
						pass
						'''
						try:
							bus_all()
						except Exception:
							send_mail('Bus_all error...')
						'''
					last_d = cur_d

			for i in l:
				var = l[i]
				if i not in running and var[1] <= ct and ct < var[2]:
					thr = threading.Thread(target = line_thread, args = (i, get_url(var[0], var[-1]), var[2], stop_l, var[-1]))
					running[i] = thr
					thr.start()
					time.sleep(2)
	except KeyboardInterrupt:
		print('Ctrl-C detected. Stopping...')
		pass

	stop_l.append(True)
	for i in running:
		running[i].join()
	ping_thr.join()

from lines import LINES, PING_LINES

if __name__ == '__main__':
	# main(LINES, PING_LINES)
	main_new(LINES, PING_LINES)
	# upd_routes(LINES)




email_sent = [False, False]
def get_req(url, endt = None, meth = 0, stop_l = [], get_line = False):
	global WX_HEADERS, email_sent
	err_code = None
	err = None
	res = None
	timeout = 3.05
	tries = 0
	intv = 1
	res_json = None
	bus_url, line_url = url
	if get_line:
		cur_url = line_url
	else:
		cur_url = bus_url
	while (tries == 0 or (endt is None or cur_time() < endt)) and not stop_l:
		try:
			if meth == 10:
				assert get_line is False
				url, data = bus_url
				res = requests.post(url, json = data, headers = SHA_HEADERS)
				get_t = time.localtime()
				res.raise_for_status()
				res = res.json()
				if res.get('code', None) != '200':
					if 'errcode' in res or tries >= 3:
						err_code = 10
						assert False, f'Error in meth 10!, {res}'
					assert False, res
				res_json = res

				url, data, direction = line_url
				res = requests.post(url, json = data, headers = SHA_HEADERS)
				res.raise_for_status()
				res = res.json()
				assert res.get('code', None) == '200', res
				res = res['data'][f'lineResults{direction}']
				assert res['direction'] == ('true' if direction == 0 else 'false'), 'Direction?'
				res = res['stop']
				res_json['_line'] = res
				break

			if meth == 9:
				assert get_line is False
				res = requests.post(bus_url, timeout = timeout)
				get_t = time.localtime()
				res.raise_for_status()
				res = etree.fromstring(res.content, etree.XMLParser())
				res = res[0]
				def proc_xml(elem):
					return {i.tag: i.text for i in elem}
				res_json = {'data': [proc_xml(elem) for elem in res]}

				station_url, schedule_url, upDown = line_url
				line_res = requests.get(station_url, timeout = timeout)
				line_res.raise_for_status()
				line_res = line_res.json()
				line_res = line_res['zdly']['false' if upDown == 1 else 'true']

				sch_res = requests.get(schedule_url, timeout = timeout)
				sch_res.raise_for_status()
				sch_res = sch_res.json()
				res_json['_line'] = {
					'line': line_res,
					'sch' : sch_res,
				}
				break

			if meth == 5:
				assert get_line is False
				res = requests.get(bus_url, timeout = timeout)
				get_t = time.localtime()
				res.raise_for_status()
				res_json = res.json()
				# res_json['_line'] = None
				line_res = requests.get(line_url, timeout = timeout)
				line_res.raise_for_status()
				res_json['_line'] = line_res.json()
				break

			if meth == 2:
				data, url = cur_url
				res = requests.post(url, data = data, headers = ZSCX_HEADERS, timeout = timeout)
				get_t = time.localtime()
				res.raise_for_status()
				res_json = res.json()
			elif meth == 4:
				res = requests.get(cur_url, headers = WX_HEADERS, timeout = timeout)
				get_t = time.localtime()
				res.raise_for_status()
				res_json = res.json()
				if upd_wuxi_token(res_json) is True:
					continue
			else:
				if meth == 6:
					res = requests.get(cur_url, headers = KS_HEADERS, timeout = timeout)
				elif meth == 11:
					res = requests.get(cur_url, headers = TC_HEADERS, timeout = timeout)
				elif meth == 7 and get_line:
					url, data = cur_url
					res = requests.post(url, json = data, timeout = timeout)
				else:
					res = requests.get(cur_url, timeout = timeout)
				get_t = time.localtime()
				res.raise_for_status()
				if meth == 0:
					rtext = res.text
					assert rtext.startswith('**YGKJ') and rtext.endswith('YGKJ##')
					rtext = rtext[6:-6]
					res_json = json.loads(rtext)
				else:
					res_json = res.json()
					if meth == 11:
						if res_json.get('result', None) != 0 or res_json.get('message', None) != 'success':
							err_code = 11
							assert False, f'Error in meth 11!, {res}'

		except Exception as e:
			if get_line:
				if 'Client Error' in str(e) or err_code is not None:
					raise
				print(f'Error {e}')
				time.sleep(3)
				continue

			print_log(f'{e} {url}')

			if err_code is not None:
				if err_code == 10:
					if not email_sent[1]:
						email_sent[1] = True
						send_mail('SH Error!')
				elif err_code == 11:
					if not email_sent[2]:
						email_sent[2] = True
						send_mail('TC Error!')
				else:
					assert False
				raise

			sleep_intr(intv, stop_l)
			err = e
			tries += 1
			if tries in (3, 6):
				timeout += 3.05
			if intv < 20 and tries >= 3:
				intv += 1
				if tries > 3:
					intv += 1
			if '429 Client Error: Too Many Requests' in str(e):
				sleep_intr(max(30 - intv, 1), stop_l)
			elif 'Client Error' in str(e) and tries >= 3:
				if not email_sent[0]:
					email_sent[0] = True
					send_mail('4XX Client Error!')
				raise
				# sleep_intr(3600, stop_l)
		else:
			break

	if res_json is None:
		assert False, 'Network error!'
	time.sleep(2)
	res_json['_meth'] = meth
	return res_json, get_t
	# raise err
	# return None



def line_thread(name, url, endt, stop_l, meth):
	try:
		t = time.time()
		while cur_time() < endt and not stop_l:
			t += INTV
			t0 = time.time()
			try:
				res, get_t = get_req(url, endt = endt, meth = meth, stop_l = stop_l)
			except Exception as e:
				print_log(type(e), e, name)
				return
			t0 = time.time() - t0
			print_log(f'[{time.strftime("%m/%d %X")}] Delay: {t0}s. {name}')
			fname = time.strftime(f'{JSON_DIR}/{name}_%y%m%d_%H%M%S.json', get_t)
			with open(fname, 'w', encoding='utf-8') as f:
				json.dump(res, f, ensure_ascii = False, indent = '\t')
			x = t - time.time()
			if x > 0:
				sleep_intr(x, stop_l)
			t = time.time()
	except KeyboardInterrupt:
		return



def get_url(line_info, meth):
	if meth == 11:
		lineId = line_info
		url = f'https://app.tcjyj.xyz/BusService/MiniApps/Query_BusBySegmentID?segmentId={lineId}'
		line_url = f'https://app.tcjyj.xyz/BusService/MiniApps/Query_CrowdBySegmentID?segmentId={lineId}'
		return (url, line_url)

	if meth == 9:
		lineId, upDown = line_info
		url = f'https://wx.jd-bus.com:1443/api/carMonitor_new?my=aa&t=bb&lineid={lineId}&direction={upDown}'
		station_url = f'https://wx.jd-bus.com:1443/api/getAllLdly?my=aa&t=bb&lineid={lineId}'
		schedule_url = f'https://wx.jd-bus.com:1443/api/line_schedule?my=aa&t=bb&lineid={lineId}&direction={upDown}'
		line_url = (station_url, schedule_url, upDown)
		return (url, line_url)

	if meth == 2:
		bus_info, l_info_ = line_info
		l_info = bus_info.copy()
		l_info.update(l_info_)
		return ((bus_info, 'https://wx.mygolbs.com/WxBusServer/ApiData.do'),
				(l_info, 'https://wx.mygolbs.com/WxBusServer/ApiData.do'),)

	if meth == 4:
		route_id, seg_id = line_info
		url = f'https://wxms.wxbus.com.cn/BusService/MiniApps/Query_BusBySegmentID?segmentId={seg_id}'
		line_url = f'https://wxms.wxbus.com.cn/BusService/MiniApps/Require_RouteStatData?routeId={route_id}'
		return (url, line_url)

	if meth == 5:
		line_guid = line_info
		url = f'https://szgj.2500.tv/api/v1/busline/bus?line_guid={line_guid}'
		line_url = f'https://szgj.2500.tv/api/v1/busline/station?line_guid={line_guid}&token={SZ_TOKEN}'
		return (url, line_url)

	if meth == 6:
		lineId, upDown = line_info
		url = f'https://zsgj.ksbus.com.cn//realInfo/vehPosiLine?lineId={lineId}&updown={upDown}&curStationNum=1&planReturn=1&max=2'
		line_url = f'https://zsgj.ksbus.com.cn//line/basic/{lineId}'
		return (url, line_url)

	if meth == 3:
		lineId, upDown = line_info
		url = f'https://czxxcxapi.czsmk.com:30003/bus/CzBus/V4.1/Bus/GetList?Line_Id={lineId}&Line_Type={upDown}'
		line_url = f'https://czxxcxapi.czsmk.com:30003/bus/CzBus/V4.1/Station/GetListByLine?Line_Id={lineId}&Line_Type={upDown}'
		return (url, line_url)

	if meth == 1:
		lineId, upDown = line_info
		url = f'http://api.dyjtx.dyszt.com:2888/dybus/route/getLineList?lineId={lineId}&upDown={upDown}'
		return (url, None)

	if meth == 7:
		liguid, lbguid, ismain = line_info
		if isinstance(liguid, str):
			assert len(liguid) == 36
		else:
			lineId, upDown = liguid
			liguid = f'{lineId:{upDown}>36d}'
		url = f'https://www.csxapi.cn/busdata/{liguid}/buses'
		line_url = 'https://www.csxapi.cn/app/nearby/detailStandsByLbguid'
		line_dict = {
			'liguid': liguid,
			'lbguid': '1',
			'ismain': ismain,
		}
		return (url, (line_url, line_dict))
	if meth == 8:
		lineId, upDown = line_info
		url = f'https://yghy.e-haoyun.com/wxApi/lineApi/findLineInfo?lineId={lineId}&direction={upDown}'
		return (url, None)

	if meth == 10:
		name, lineId, stopId, direction = line_info

		url = 'https://smartgate.ywtbsupappw.sh.gov.cn/ebus/jtw/trafficline/carmonitor/v2'
		d = {
			'name': name,
			'lineid': lineId,
			'stopid': stopId,
			'direction': direction,
		}
		data = SHA_DATA.copy()
		data['params'] = d
		data.update(d)

		line_url = 'https://smartgate.ywtbsupappw.sh.gov.cn/ebus/jtw/trafficline/stoplist/v2'
		d = {
			'name': name,
			'lineid': lineId,
		}
		line_data = SHA_DATA.copy()
		line_data['params'] = d
		line_data.update(d)

		return ((url, data), (line_url, line_data, direction))

	assert meth == 0

	# cityId, lineId, lng, lat = line_info
	cityId, lineId = line_info
	lng = 118.8
	lat = 32

	url = f'https://api.chelaile.net.cn/bus/line!lineDetail.action?sign=PPgBLFF5779koWJpY09iQg%3D%3D' + \
		f'&cityId={cityId}&geo_type=gcj&lineId={lineId}&isNewLineDetail=1&s=android' + \
		f'&last_src=app_xiaomi_store&geo_lng={lng}&geo_lat={lat}&v=3.80.0'

	return (url, None)

