from .base import CrawlerBase
from .util import SZ_TOKEN


class Suzhou(CrawlerBase):
	METH = 5
	GET_LINE = False
	def __init__(self, bus_name, line_info):
		super().__init__(bus_name, line_info)
		line_guid = line_info
		self.bus_url  = f'https://szgj.2500.tv/api/v1/busline/bus?line_guid={line_guid}'
		self.line_url = f'https://szgj.2500.tv/api/v1/busline/station?line_guid={line_guid}&token={SZ_TOKEN}'


	def get_stations(self, line_json):
		stations = [(s['standName'], None, None) for s in line_json['standInfo']]
		return stations


	# 13, 0 : 13 -> 14
	# 13, 1 : at 13
	def proc(self, res_json):
		line_json = res_json['_line']
		station_data = [i['standSguid'] for i in line_json['standInfo']]

		bus_datas = []
		if 'standInfo' in res_json:
			if isinstance(res_json['standInfo'], list):
				assert not res_json['standInfo'], f'List of standInfo must be empty!'
			else:
				for station_id, bds in res_json['standInfo'].items():
					if station_id in station_data:
						station_id = station_data.index(station_id)
					elif station_id == 'b50cf4ee-f3e1-498f-abce-547eedca6d90':
						station_id = 0
					else:
						NONE_LIST = ['71a2d770-7fed-4744-afad-24090ccc18dd',
									 '11e58807-dcd7-4b07-81cd-ba00430bed21',]
						if station_id in NONE_LIST and station_data.count(None) == 1:
							station_id = station_data.index(None)
						else:
							raise ValueError(f'"{station_id}" not in station_data')

					for bus_data in bds:
						bus_id = bus_data['busInfo']
						if isinstance(bus_id, list):
							assert not bus_id, f'List of busInfo must be empty!'
							continue
						in_station = 0
						lon = None
						lat = None
						bus_datas.append((bus_id, station_id, in_station, lon, lat))

		return bus_datas, line_json


	def _get_once(self, get_line = False, **kwargs):
		def get_func(url):
			res_json, get_t = self._get_json(url, **kwargs)
			if res_json['code'] == '100501' and res_json['msg'] == '请求失败':
				return None, None
			if res_json['code'] != '0' and res_json['msg'] != '':
				assert False, f'Failed! code: {res_json["code"]}, msg: {res_json["msg"]}'
			res_json = res_json['data']
			return res_json, get_t

		res_json, get_t = get_func(self.bus_url)
		if res_json is None and get_t is None:
			return None, None

		line_json, t = get_func(self.line_url)
		if line_json is None and t is None:
			return None, None

		res_json['_line'] = line_json

		return res_json, get_t

