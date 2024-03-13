from .base import CrawlerBase
from .util import KS_TOKEN, send_mail

KS_HEADERS = {
	'token': KS_TOKEN,
}


class Kunshan(CrawlerBase):
	METH = 6
	GET_LINE = True
	def __init__(self, bus_name, line_info):
		super().__init__(bus_name, line_info)
		lineId, upDown = line_info
		self.bus_url  = f'https://zsgj.ksbus.com.cn//realInfo/vehPosiLine?lineId={lineId}&updown={upDown}&curStationNum=1&planReturn=1&max=2'
		self.line_url = f'https://zsgj.ksbus.com.cn//line/basic/{lineId}'
		self.upDown = upDown


	def get_stations(self, line_json):
		stations = [(s['stationName'], None, None) for s in line_json['station']]
		return stations


	# 13, 0 : 13 -> 14
	# 13, 1 : at 13
	def proc(self, res_json):
		def _proc(bus_data):
			in_station = bus_data['inStation']
			lon = None
			lat = None
			return (bus_data['veh'], bus_data['nextStationNum'] - (1 - in_station) - 1, in_station, lon, lat)

		bus_datas = [_proc(i) for i in res_json['vehPosiList']]
		return bus_datas, None


	def _get_once(self, get_line = False, **kwargs):
		try:
			res_json, get_t = super()._get_once(get_line = get_line, headers = KS_HEADERS, **kwargs)
		except Exception as e:
			import re
			str_e = str(e)
			if 'Client Error' in str_e and 'Too Many Requests' not in str_e:
				self._stop = True
				if self.METH not in self.EMAIL_SENT:
					self.EMAIL_SENT[self.METH] = 1
					send_mail(f'Kunshan Error!')
			raise

		if res_json.get('code', None) != 0:
			assert False, f'Failed! code: {res_json.get("code", None)}'

		res_json = res_json['data']
		
		if get_line:
			slist_name = 'stationListUp' if self.upDown == 0 else 'stationListDown'
			res_json['station'] = res_json[slist_name]
			del res_json['stationListUp']
			del res_json['stationListDown']

		return res_json, get_t

