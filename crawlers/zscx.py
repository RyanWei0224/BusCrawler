from .base import CrawlerBase
from .util import ZSCX_HEADERS


class ZSCX(CrawlerBase):
	METH = 2
	GET_LINE = True
	def __init__(self, bus_name, line_info):
		super().__init__(bus_name, line_info)
		bus_info, l_info = line_info
		self.bus_url   = 'https://wx.mygolbs.com/WxBusServer/ApiData.do'
		self.line_url  = 'https://wx.mygolbs.com/WxBusServer/ApiData.do'
		self.bus_data  = bus_info
		self.line_data = bus_info.copy()
		self.line_data.update(l_info)


	def get_stations(self, line_json):
		stations = [s['stationName'] for s in line_json['data']]
		return stations


	# 13, 0 : 13 -> 14
	# 13, 1 : at 13
	def proc(self, res_json):
		def _proc(bus_data):
			station_id = bus_data['index']
			in_station = 1 if bus_data['busToStationNiheDistance'] <= 20.00 else 0
			station_id -= (1 - in_station)
			lon = bus_data.get('bus_lng', None)
			lat = bus_data.get('bus_lat', None)
			return (bus_data['busNumber'], station_id, in_station, lon, lat)

		bus_datas = [_proc(i) for i in res_json['list']]
		return bus_datas, None


	def _get_once(self, get_line = False, **kwargs):
		if get_line:
			url, data = self.line_url, self.line_data
		else:
			url, data = self.bus_url, self.bus_data
		res, get_t = self._get_req(url, data = data, headers = ZSCX_HEADERS)
		try:
			res_json = res.json()
		except Exception as e:
			print(f'ZSCX content: "{res.content}"')
			raise

		if res_json['status'] != 1 and res_json['msg'] != '获取实时数据成功!':
			assert False, f'Failed! status: {res_json["status"]}, msg: {res_json["msg"]}'

		return res_json, get_t

