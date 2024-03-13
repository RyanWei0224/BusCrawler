from .base import CrawlerBase


class Changzhou(CrawlerBase):
	METH = 3
	GET_LINE = True
	def __init__(self, bus_name, line_info):
		super().__init__(bus_name, line_info)
		lineId, upDown = line_info
		self.bus_url  = f'https://czxxcxapi.czsmk.com:30003/bus/CzBus/V4.1/Bus/GetList?Line_Id={lineId}&Line_Type={upDown}'
		self.line_url = f'https://czxxcxapi.czsmk.com:30003/bus/CzBus/V4.1/Station/GetListByLine?Line_Id={lineId}&Line_Type={upDown}'


	def get_stations(self, line_json):
		def _proc(s):
			if 'LatLng' not in s:
				lon = None
				lat = None
			else:
				lon = s['LatLng'].get('longitude', None)
				lat = s['LatLng'].get('latitude', None)
			return (s['Station_Name'], lon, lat)
		stations = [_proc(s) for s in line_json]
		return stations


	# 13, 0 : 13 -> 14
	# 13, 1 : at 13
	def proc(self, res_json):
		def _proc(bus_data):
			if 'LatLng' not in bus_data:
				lon = None
				lat = None
			else:
				lon = bus_data['LatLng'].get('longitude', None)
				lat = bus_data['LatLng'].get('latitude', None)
			# "RecTime": "2024-03-11 14:35:34"
			return (bus_data['BusId'], bus_data['Current_Station_Sort'] - 1, bus_data['IsArrive'], lon, lat)

		bus_datas = [_proc(i) for i in res_json]
		return bus_datas, None


	def _get_once(self, get_line = False, **kwargs):
		res_json, get_t = super()._get_once(get_line = get_line, **kwargs)

		if res_json['resCode'] != 10000 and res_json['resMsg'] != '成功':
			assert False, f'Failed! resCode: {res_json["resCode"]}, resMsg: {res_json["resMsg"]}'
		res_json = res_json['value']

		return res_json, get_t

