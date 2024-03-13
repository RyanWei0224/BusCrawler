import json
import time
import requests
import threading
import os

from mail import send_mail
from read_bus import main as read_bus

JSON_DIR = 'json'

INTV = 11

'''
method:
0: cll
1: dy
2: zscx
3: czx
4: wx
5: sz
6: ks
7: cs
'''

from config import ZSCX_HEADERS, WX_TOK_JSON, KS_HEADERS, SZ_TOKEN, CLL_SIGN

WX_TOK_URL = 'https://wxms.wxbus.com.cn/BusService/MiniApps/QueryToken'

WX_HEADERS = {
	'token': '',
}

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
	with open('bus.log', 'a', encoding = 'utf-8') as f:
		print(*args, file = f, **kwargs)
	if verbose:
		print(*args, **kwargs)

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


def get_req(url, endt = None, meth = 0, stop_l = []):
	global WX_HEADERS
	err = None
	res = None
	timeout = 3.05
	tries = 0
	intv = 1
	while (tries == 0 or (endt is None or cur_time() < endt)) and not stop_l:
		try:
			# 
			if meth == 2:
				data, bus_url = url
				res = requests.post(bus_url, data = data, headers = ZSCX_HEADERS, timeout = timeout)
				get_t = time.localtime()
				res.raise_for_status()
				res_json = res.json()
			elif meth == 4:
				bus_url, line_url = url
				res = requests.get(bus_url, headers = WX_HEADERS, timeout = timeout)
				get_t = time.localtime()
				res.raise_for_status()
				res_json = res.json()
				if upd_wuxi_token(res_json) is True:
					continue
				res_json['_line'] = None
				'''
				line_res = requests.get(line_url, headers = WX_HEADERS, timeout = timeout)
				line_res.raise_for_status()
				res_json['_line'] = line_res.json()
				if upd_wuxi_token(res_json['_line']) is True:
					continue
				'''
			elif meth == 5:
				bus_url, line_url = url
				res = requests.get(bus_url, timeout = timeout)
				get_t = time.localtime()
				res.raise_for_status()
				line_res = requests.get(line_url, timeout = timeout)
				line_res.raise_for_status()
				res_json = res.json()
				res_json['_line'] = line_res.json()
			else:
				if meth == 6:
					res = requests.get(url, headers = KS_HEADERS, timeout = timeout)
				else:
					res = requests.get(url, timeout = timeout)
				get_t = time.localtime()
				res.raise_for_status()
				if meth == 0:
					rtext = res.text
					assert rtext.startswith('**YGKJ') and rtext.endswith('YGKJ##')
					rtext = rtext[6:-6]
					res_json = json.loads(rtext)
				else:
					res_json = res.json()
		except Exception as e:
			print_log(e)
			time.sleep(intv)
			err = e
			tries += 1
			if tries in (3, 6):
				timeout += 3.05
			if intv < 20 and tries >= 3:
				intv += 1
				if tries > 3:
					intv += 1
			if '429 Client Error: Too Many Requests' in str(e):
				time.sleep(max(30 - intv, 1))
			elif 'Client Error' in str(e) and tries >= 3:
				send_mail('4XX Client Error!')
				sleep_intr(3600, stop_l)
		else:
			time.sleep(2)
			res_json['_meth'] = meth
			return res_json, get_t
	raise err
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
			print_log(f'Delay: {t0}s. {name}')
			fname = time.strftime(f'{JSON_DIR}/{name}_%y%m%d_%H%M%S.json', get_t)
			with open(fname, 'w', encoding='utf-8') as f:
				json.dump(res, f, ensure_ascii = False, indent = '\t')
			x = t - time.time()
			if x > 0:
				sleep_intr(x, stop_l)
			else:
				t = time.time()
	except KeyboardInterrupt:
		return



def get_url(line_info, meth):
	if meth == 2:
		return (line_info, 'https://wx.mygolbs.com/WxBusServer/ApiData.do')

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
		return url

	if meth == 3:
		lineId, upDown = line_info
		url = f'https://czxxcxapi.czsmk.com:30003/bus/CzBus/V4.1/Bus/GetList?Line_Id={lineId}&Line_Type={upDown}'
		return url

	if meth == 1:
		lineId, upDown = line_info
		url = f'http://api.dyjtx.dyszt.com:2888/dybus/route/getLineList?lineId={lineId}&upDown={upDown}'
		return url

	if meth == 7:
		lineId, upDown = line_info
		url = f'https://www.csxapi.cn/busdata/{lineId:{upDown}>36d}/buses'
		return url

	cityId, lineId, lng, lat = line_info

	url = f'https://api.chelaile.net.cn/bus/line!lineDetail.action?sign={CLL_SIGN}' + \
		f'&cityId={cityId}&geo_type=gcj&lineId={lineId}&isNewLineDetail=1&s=android' + \
		f'&last_src=app_xiaomi_store&geo_lng={lng}&geo_lat={lat}&v=3.80.0'

	return url


l = {
	#'TEST'    : (['018', '0025114985354', 118.980792, 32.121315], CT(17, 3), CT(23, 0), 0),
	#'TEST2'   : (['018', '0025114985347', 118.980792, 32.121315], CT(17, 0), CT(23, 18), 0),
	'NJ_34'   : (['018', '0025106077894', 118.8, 32], CT(5, 20), CT(5, 50), 0),
	'NJ_Y1'   : (['018', '0025114984326', 118.8, 32], CT(4, 30), CT(5, 0), 0),
	'NJ_Y2'   : (['018', '0025114985051', 118.8, 32], CT(4, 35), CT(5, 10), 0),
	'NJ_Y5'   : (['018', '0025114985685', 118.8, 32], CT(4, 40), CT(6, 30), 0),
	'NJ_Y8'   : (['018', '0025114985766', 118.8, 32], CT(4, 30), CT(5, 0), 0),
	'NJ_Y13'  : (['018', '0025114984461', 118.8, 32], CT(4, 50), CT(5, 20), 0),
	'NJ_Y14'  : (['018', '0025114984486', 118.8, 32], CT(5, 0), CT(6, 30), 0),
	'NJ_Y17'  : (['018', '0025114984573', 118.802216, 31.983826], CT(5, 10), CT(5, 40), 0),
	'NJ_Y34'  : (['018', '0025114985354', 118.980792, 32.121315], CT(5, 10), CT(6, 10), 0),
	'ZJ_606'  : (['098',  '511138990510', 119.467577, 32.193444], CT(6, 20), CT(9, 20), 0),
	'ZJ_633'  : (['098', '0511159468448', 119.629825, 32.019042], CT(7, 55), CT(10, 5), 0),
	'ZJ_302'  : (['098',  '511138990451', 119.398026, 31.871026], CT(7, 0), CT(9, 45), 0),
	#'DY_1'    : ([ 1, 2], CT(8, 40), CT(9, 35), 1),
	'DY_7'    : ([ 6, 2], CT(8, 40), CT(9, 35), 1),
	'DY_15'   : ([13, 1], CT(8, 40), CT(9, 35), 1),
	'DY_15Z'  : ([14, 1], CT(8, 40), CT(9, 35), 1),
	#'DY_27'   : ([25, 1], CT(8, 40), CT(9, 35), 1),
	'DY_208'  : ([37, 2], CT(8, 55), CT(10, 40), 1),
	'DY_209'  : ([38, 2], CT(8, 55), CT(10, 40), 1),
	'DY_209Z' : ([39, 2], CT(8, 55), CT(10, 40), 1),
	#'DY_212'  : ([41, 2], CT(8, 55), CT(10, 40), 1),
	'DY_212Z' : ([42, 2], CT(8, 55), CT(10, 40), 1),
	'JT_331'  : (['058', '0519258847346', 119.378326, 31.832636], CT(9, 35), CT(10, 5), 0),
	'CZ_88'   : (['058',  '519237736866', 119.874056, 31.775086], CT(10, 0), CT(11, 30), 0),
	'CZ_89'   : (['058', '0519253978784', 119.960636, 31.673606], CT(10, 0), CT(12, 30), 0),
	'CZ_34'   : (['058',  '519237736657', 119.956397, 31.787943], CT(9, 50), CT(11, 40), 0),
	'CZ_B1'   : (['058',  '519237736859', 119.971062, 31.677410], CT(11, 0), CT(12, 40), 0),
	'CZ_68'   : (['058',  '519237736807', 120.111833, 31.517845], CT(12, 0), CT(14, 10), 0),
	'CZ_517'  : (['058',  '519237736887', 119.957416, 31.715696], CT(10, 20), CT(12, 0), 0),
	'CZ_K1'   : (['058',  '519237737023', 119.957416, 31.715696], CT(11, 15), CT(15, 10), 0),

	'CZR_B1'  : ([81, 2], CT(11, 0),  CT(12, 40), 3),
	'CZR_88'  : ([88, 2], CT(10, 0),  CT(11, 30), 3),
	'CZR_89'  : ([89, 2], CT(8, 50),  CT(12, 30), 3),
	'CZR_89R'  : ([89, 1], CT(8, 50),  CT(12, 30), 3),
	'CZR_68'  : ([68, 2], CT(12, 0),  CT(14, 10), 3),
	'CZR_K1'  : ([451, 2], CT(11, 15), CT(15, 10), 3),

	'JR_BT'   : ({
					'CMD': 104,
					'LINENAME': '白兔线',
					'DIRECTION': 1,
					'CITYNAME': '句容市',
					'TIMESTAMP': 1689438537059,
					'SIGN': 'ec302c8dce0b1ce5ffe5ad3fd6e54bef',
				}, CT(5, 55), CT(9, 30), 2),

	'WX_26'  : (['054', '510174331137', 120.272856, 31.577046], CT(12, 30), CT(16, 30), 0),
	'WX_WT'  : (['054', '510174331567', 120.436316, 31.432066], CT(14, 0), CT(18, 0), 0),
	'WX_G1'  : (['054', '510174331333', 120.393586, 31.524266], CT(13, 45), CT(17, 0), 0),

	'WXR_26' : ([26, -30138005], CT(12, 30), CT(16, 30), 4),
	'WXR_WT' : ([7001, 34436710], CT(14, 0), CT(18, 0), 4),
	'WXR_G1' : ([101, -22341111], CT(13, 45), CT(17, 0), 4),

	'SZR_SX1' : ('a8c34320-bf3b-4588-97f2-aec8f6996276', CT(14, 0), CT(19, 0), 5),
	'SZR_85'  : ('F2439A59-45A2-4596-BD31-529CE8C54877', CT(16, 0), CT(18, 40), 5),
	'SZR_KX9' : ('3e203187-0fac-74cc-a42b-43f69344b385', CT(18, 0), CT(19, 35), 5),
	'SZR_158' : ('21aea961-b944-4b41-919f-e1e31049e254', CT(18, 0), CT(19, 35), 5),

	'WXR_126' : ([126, 34436712], CT(13, 50), CT(15, 30), 4),
	'WXR_712' : ([712, -24213010], CT(14, 50), CT(16, 50), 4),
	'SZR_83'  : ('63D974A5-C634-A788-07C7-85C6D3F9C3B7', CT(16, 0), CT(18, 20), 5),
	'SZR_KX7' : ('a5613a40-901a-4c92-ae3f-6225b249d7e6', CT(17, 20), CT(19, 0), 5),
	'SZR_113' : ('c084f619-9802-4237-87fe-f732ef0eaf14', CT(18, 50), CT(19, 25), 5),

	'SZR_SX1_2' : ('9b5b8b7c-4d2b-41b5-94a1-7d9ec00657be', CT(9, 25), CT(11, 20), 5),
	'WX_26_2'   : (['054', '510174331138', 120.100446, 31.513286], CT(11, 20), CT(13, 0), 0),
	'WXR_26_2'  : ([26, 30138005], CT(11, 20), CT(13, 0), 4),
	'WXR_WT_2'  : ([7001, -34436710], CT(9, 55), CT(11, 0), 4),
	'CZR_68_2'  : ([68, 1], CT(11, 45),  CT(14, 10), 3),
	'CZR_89_2'  : ([89, 1], CT(12, 45),  CT(15, 20), 3),
	'CZR_89_2R'  : ([89, 2], CT(12, 45),  CT(15, 20), 3),
	'ZJ_302_2'  : (['098',  '511138990450', 119.427476, 32.200926], CT(16, 10), CT(17, 10), 0),

	'JR_BT_2'   : ({
					'CMD': 104,
					'LINENAME': '白兔线',
					'DIRECTION': 2,
					'CITYNAME': '句容市',
					'TIMESTAMP': 1689823559995,
					'SIGN': 'd1df6219642c4b28cbedc0060c580cb4',
				}, CT(16, 30), CT(18, 15), 2),

	'KS_C2'   : ([951, 1], CT(18, 55), CT(20, 40), 6),
	'KS_101'  : ([311, 1], CT(19, 30), CT(21, 20), 6),
	'KS_102'  : ([451, 1], CT(19, 50), CT(21, 40), 6),
	'KS_126'  : ([431, 0], CT(19, 00), CT(20, 20), 6),
	'KS_HQ228': ([301, 0], CT(20, 30), CT(21, 45), 6),
	'KS_HQX1' : ([1194, 0], CT(20, 20), CT(21, 20), 6),

	#'CS_202'  : ([202, 's'], CT(15, 50), CT(18, 30), 7),
	#'CS_2021' : ([2021, 's'], CT(15, 50), CT(18, 30), 7),
	#'TC_123'  : (['281', '512151323338', 121.073, 31.440], CT(17, 50), CT(19, 30), 0),
}

'''
	'JR_YJ2'   : ({
					'CMD': 104,
					'LINENAME': '拥2线',
					'DIRECTION': 2,
					'CITYNAME': '句容市',
					'TIMESTAMP': 1691164900267,
					'SIGN': 'db53d0167a3338f54d8f30596a1500bc',
				}, CT(6, 25), CT(, 30), 2),
'''

'''

	'WXZ_26'   : ({
					'CMD': 104,
					'LINENAME': '26路',
					'DIRECTION': 2,
					'CITYNAME': '无锡市',
					'TIMESTAMP': 1689534480456,
					'SIGN': 'cec040c802ce4d3cb5acf1497beb2fa3',
				}, CT(12, 30), CT(16, 30), 2),

	'WXZ_WT'   : ({
					'CMD': 104,
					'LINENAME': '望亭专线',
					'DIRECTION': 1,
					'CITYNAME': '无锡市',
					'TIMESTAMP': 1689534563265,
					'SIGN': '0977e719ee1574e3ac2e2076c963a647',
				}, CT(14, 0), CT(18, 0), 2),

	'WXZ_G1'   : ({
					'CMD': 104,
					'LINENAME': 'G1线',
					'DIRECTION': 2,
					'CITYNAME': '无锡市',
					'TIMESTAMP': 1689534625042,
					'SIGN': '2b49e13ea6fb1f49c766ffae27c4ab3a',
				}, CT(13, 45), CT(17, 0), 2),
'''

'''
	'TESTWX'  : ([101, -22341111], CT(1, 45), CT(17, 0), 4),
	'TESTSZ' : ('a8c34320-bf3b-4588-97f2-aec8f6996276', CT(2, 0), CT(19, 0), 5),
	'TESTKS'   : ([951, 1], CT(1, 55), CT(20, 40), 6),
'''


STATIONS = {
	'ZJ_302'  : {
		7: '南门汽车客运站',
		19: '白兔桥',
		23: '荣炳公交站',
	}
}

def main():
	running = dict()
	stop_l = []

	if not os.path.isdir(JSON_DIR):
		os.mkdir(JSON_DIR)

	last_d = cur_date()

	try:
		while True:
			time.sleep(1)
			ct = cur_time()
			if ct < CT(1, 0):
				if running:
					for i in running:
						running[i].join()
					running = dict()
				cur_d = cur_date()
				if last_d != cur_d:
					ret = read_bus(per_bus = False)
					if ret is None or not ret:
						send_mail('Read bus error...')
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

if __name__ == '__main__':
	main()
