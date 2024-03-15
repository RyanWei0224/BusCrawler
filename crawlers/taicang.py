from .base import CrawlerBase
from .util import TC_TOKEN, send_mail

TC_HEADERS = {
	'token': TC_TOKEN,
}


class Taicang(CrawlerBase):
	METH = 11
	GET_LINE = True
	def __init__(self, bus_name, line_info):
		super().__init__(bus_name, line_info)
		lineId = line_info
		self.bus_url  = f'https://app.tcjyj.xyz/BusService/MiniApps/Query_BusBySegmentID?segmentId={lineId}'
		self.line_url = f'https://app.tcjyj.xyz/BusService/MiniApps/Query_CrowdBySegmentID?segmentId={lineId}'
		if TC_TOKEN is None:
			self._stop = True


	@classmethod
	def get_stations(cls, line_json):
		stations = [(s['stationName'], None, None) for s in line_json]
		return stations


	# 13, 0 : 13 -> 14
	# 13, 1 : at 13
	def proc(self, res_json):
		def _proc(bus_data):
			in_station = 0 if bus_data['inoutType'] == 1 else 1
			if in_station != 0:
				print(f'Taicang: type {bus_data["inoutType"]}')
			lon = bus_data.get('lng', None)
			lat = bus_data.get('lat', None)
			return (bus_data['busName'], bus_data['arriveStationNo'] - 1, in_station, lon, lat)

		bus_datas = [_proc(i) for i in res_json]
		return bus_datas, None


	def _get_once(self, get_line = False, **kwargs):
		res_json, get_t = super()._get_once(get_line = get_line, headers = TC_HEADERS, **kwargs)

		if res_json.get('result', None) != '0' or res_json.get('message', None) != 'success':
			self._stop = True
			if self.METH not in self.EMAIL_SENT:
				self.EMAIL_SENT[self.METH] = 1
				send_mail('Taicang Error!')
			assert False, f'Error in Taicang! {res_json}'

		res_json = res_json['items']

		return res_json, get_t
