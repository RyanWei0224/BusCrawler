from .base import CrawlerBase


class Zhangjiagang(CrawlerBase):
	METH = 8
	GET_LINE = False
	def __init__(self, bus_name, line_info):
		super().__init__(bus_name, line_info)
		lineId, upDown = line_info
		self.bus_url  = f'https://yghy.e-haoyun.com/wxApi/lineApi/findLineInfo?lineId={lineId}&direction={upDown}'
		self.line_url = None


	def get_stations(self, line_json):
		def _proc(s):
			lon = s.get('lng', None)
			lat = s.get('lat', None)
			return (s['stationName'], lon, lat)
		stations = [_proc(s) for s in line_json['lineStationInfo']]
		return stations


	# 13, 0 : 13 -> 14
	# 13, 1 : at 13
	def proc(self, res_json):
		def _proc(bus_data):
			assert bus_data['inoutFlag'] in (0, 1, 2), f'bus_data["inoutFlag"] is {bus_data["inoutFlag"]}'
			in_station = 1 if bus_data['inoutFlag'] != 2 else 0
			try:
				lon = float(bus_data['lon'])
			except Exception:
				lon = None
			try:
				lat = float(bus_data['lat'])
			except Exception:
				lat = None
			return (bus_data['carNo'], bus_data['sortNum'] - 1, in_station, lon, lat)

		bus_datas = [_proc(i) for i in res_json['busInfo']]
		line_json = {
			i : res_json[i] for i in ['line', 'lineStationInfo', 'lintTime']
		}
		del line_json['line']['updateTime']
		for i in line_json['lineStationInfo']:
			del i['updateTime']
		for i in line_json['lintTime']:
			del i['updateTime']
			del i['createTime']
			del i['id']
		return bus_datas, line_json


	def _get_once(self, get_line = False, **kwargs):
		res_json, get_t = super()._get_once(get_line = get_line)


		if res_json['code'] != 0 or res_json['ok'] is not True:
			assert False, f'Failed! code: {res_json["code"]}, ok: {res_json["ok"]}'

		res_json = res_json['data']
		return res_json, get_t

