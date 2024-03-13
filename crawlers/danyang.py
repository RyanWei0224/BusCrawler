from .base import CrawlerBase


class Danyang(CrawlerBase):
	METH = 1
	GET_LINE = False
	def __init__(self, bus_name, line_info):
		super().__init__(bus_name, line_info)
		lineId, upDown = line_info
		self.bus_url  = f'http://api.dyjtx.dyszt.com:2888/dybus/route/getLineList?lineId={lineId}&upDown={upDown}'
		self.line_url = None


	def get_stations(self, line_json):
		def _proc(s):
			lon = s.get('inLon', None)
			lat = s.get('inLat', None)
			return (s['stationName'], lon, lat)
		stations = [_proc(s) for s in line_json['stationDetailList']]
		return stations


	# 13, 0 : 13 -> 14
	# 13, 1 : at 13
	def proc(self, res_json):
		station_data = res_json['stationDetailList']
		station_data = [station['stationId'] for station in station_data]

		bus_datas = []
		for bus_data in res_json['busList']:
			if 'stationId' not in bus_data:
				continue
			station_id = bus_data['stationId']
			lon = bus_data.get('lon', None)
			lat = bus_data.get('lat', None)
			res = (bus_data['busId'], station_data.index(station_id), 2-int(bus_data['busStatus']), lon, lat) #, None
			bus_datas.append(res)
		del res_json['busList']

		return bus_datas, res_json


	def _get_once(self, get_line = False, **kwargs):
		res_json, get_t = super()._get_once(get_line = get_line)

		if res_json.get('code', None) != 200 and res_json.get('msg', None) != '成功':
			assert False, f'Failed! code: {res_json.get("code", None)}, msg: {res_json.get("msg", None)}'
		res_json = res_json['data']
		return res_json, get_t

