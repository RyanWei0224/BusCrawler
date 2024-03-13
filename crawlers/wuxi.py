from .base import CrawlerBase
from .util import WX_TOK_JSON, send_mail

WX_TOK_URL = 'https://wxms.wxbus.com.cn/BusService/MiniApps/QueryToken'


class Wuxi(CrawlerBase):
	METH = 4
	GET_LINE = True
	WX_HEADERS = {
		'token': '',
	}
	def __init__(self, bus_name, line_info):
		super().__init__(bus_name, line_info)
		route_id, seg_id = line_info
		self.bus_url  = f'https://wxms.wxbus.com.cn/BusService/MiniApps/Query_BusBySegmentID?segmentId={seg_id}'
		self.line_url = f'https://wxms.wxbus.com.cn/BusService/MiniApps/Require_RouteStatData?routeId={route_id}'
		self.seg_id = seg_id


	def get_stations(self, line_json):
		stations = [s['stationName'] for s in line_json['stations']]
		return stations


	# 13, 0 : 13 -> 14
	# 13, 1 : at 13
	def proc(self, res_json):
		def _proc(bus_data):
			in_station = 2 - bus_data['inoutType']
			lon = bus_data.get('longitude', None)
			lat = bus_data.get('latitude', None)
			return (bus_data['busNo'], bus_data['arriveStationNo'] - 1, in_station, lon, lat)
		bus_datas = [_proc(i) for i in res_json]
		return bus_datas, None


	def _get_once(self, get_line = False, **kwargs):
		def upd_wuxi_token(data):
			try:
				import time
				time.sleep(1)
				res_json, _ = self._get_json(WX_TOK_URL, is_post = True, json = WX_TOK_JSON)
				new_token = res_json['items']['token']
				self.WX_HEADERS['token'] = new_token
				time.sleep(1)
			except Exception as e:
				print(e)
				self._stop = True
				if self.METH not in self.EMAIL_SENT:
					self.EMAIL_SENT[self.METH] = 1
					send_mail(f'Error: {e} while loading wuxi')
				raise
				# return False
			return True

		for _ in range(3):
			res_json, get_t = super()._get_once(get_line = get_line, headers = self.WX_HEADERS)
			if res_json['result'] != '2' or res_json['message'] != 'token无效或者已过期':
				break
			upd_wuxi_token(res_json)
		else:
			assert False, 'Update wuxi for 3 times!'

		if res_json['result'] != '0' and res_json['message'] != 'success':
			assert False, f'Failed! result: {res_json["result"]}, message: {res_json["message"]}'

		res_json = res_json['items']

		if get_line:
			for d in res_json:
				if str(d['segmentId']) == str(self.seg_id):
					res_json = d
					break
			else:
				assert False, f'Cannot find segment {self.seg_id}'

		return res_json, get_t

