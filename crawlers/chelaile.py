from .base import CrawlerBase
from .util import CLL_SIGN


class Chelaile(CrawlerBase):
	METH = 0
	GET_LINE = False
	def __init__(self, bus_name, line_info):
		super().__init__(bus_name, line_info)
		# cityId, lineId, lon, lat = line_info
		cityId, lineId = line_info
		lon = 118.8
		lat = 32
		self.bus_url  = f'https://api.chelaile.net.cn/bus/line!lineDetail.action?sign={CLL_SIGN}' \
			f'&cityId={cityId}&geo_type=gcj&lineId={lineId}&isNewLineDetail=1&s=android' \
			f'&last_src=app_xiaomi_store&geo_lng={lon}&geo_lat={lat}&v=3.80.0'
		self.line_url = None


	@classmethod
	def get_stations(cls, line_json):
		def _proc(s):
			lon = s.get('lng', None)
			lat = s.get('lat', None)
			return (s['sn'], lon, lat)
		stations = [_proc(s) for s in line_json['stations']]
		return stations


	# 13, 0 : 13 -> 14
	# 13, 1 : at 13
	def proc(self, res_json):
		def _proc(bus_data):
			in_station = int(bus_data['state'])
			lon = bus_data.get('lon', None)
			lat = bus_data.get('lat', None)
			return (bus_data['busId'], int(bus_data['order']) - (1 - in_station) - 1, in_station, lon, lat) #, None

		data = res_json
		bus_datas = data['buses']
		bus_datas = [_proc(i) for i in bus_datas]

		from util import dict_del
		del data['buses']
		dict_del(data, 'tip')
		dict_del(data, 'depDesc')
		dict_del(data, 'depTable')
		dict_del(data['line'], 'afterEndOperatingTimeHalfHour')
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
		return bus_datas, data


	def _get_once(self, get_line = False, **kwargs):
		url = self.line_url if get_line else self.bus_url
		res, get_t = self._get_req(url, **kwargs)
		rtext = res.text
		assert rtext.startswith('**YGKJ') and rtext.endswith('YGKJ##'), f'[Chelaile] Wrong format: {rtext}'
		rtext = rtext[6:-6]
		import json
		res_json = json.loads(rtext)

		res_json = res_json['jsonr']
		if not res_json.get('success', False):
			assert False, f'Failed! success: {res_json["success"]}, status: {res_json["status"]}, msg: {res_json.get("errmsg", "")}'
		res_json = res_json['data']

		return res_json, get_t

