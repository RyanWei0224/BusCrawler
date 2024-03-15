from .base import CrawlerBase
from .util import SH_HEADERS, SH_DATA, SH_TOKEN, send_mail


class Shanghai(CrawlerBase):
	METH = 10
	GET_LINE = False
	def __init__(self, bus_name, line_info):
		super().__init__(bus_name, line_info)
		name, lineId, stopId, direction = line_info
		self.bus_url  = 'https://smartgate.ywtbsupappw.sh.gov.cn/ebus/jtw/trafficline/carmonitor/v2'
		self.line_url = 'https://smartgate.ywtbsupappw.sh.gov.cn/ebus/jtw/trafficline/stoplist/v2'
		d = {
			'name': name,
			'lineid': lineId,
			'stopid': stopId,
			'direction': direction,
		}
		self.bus_data = SH_DATA.copy()
		self.bus_data['params'] = d
		self.bus_data.update(d)
		d = {
			'name': name,
			'lineid': lineId,
		}
		self.line_data = SH_DATA.copy()
		self.line_data['params'] = d
		self.line_data.update(d)
		self.direction = direction
		if SH_TOKEN is None:
			self._stop = True


	@classmethod
	def get_stations(cls, line_json):
		stations = [(s['zdmc'], None, None) for s in line_json]
		return stations


	# 13, 0 : 13 -> 14
	# 13, 1 : at 13
	def proc(self, res_json):
		def _proc(bus_data, tot_stop):
			rem_stop = int(bus_data['stopdis'])
			cur_stop = (tot_stop - 1) - rem_stop
			in_station = 0
			try:
				dist = int(bus_data['distance'])
			except Exception:
				dist = None
			try:
				t = int(bus_data['time'])
			except Exception:
				t = None
			return (bus_data['terminal'], cur_stop, in_station, dist, t)

		line_json = res_json['_line']
		tot_stop = len(line_json)

		bus_datas = res_json['data']
		if isinstance(bus_datas, str):
			bus_datas = []
		else:
			bus_datas = bus_datas['cars']['car']
		bus_datas = [_proc(i, tot_stop) for i in bus_datas]

		return bus_datas, line_json


	def _get_once(self, get_line = False, **kwargs):
		def check_code(res_json):
			if res_json.get('code', None) != '200' or res_json.get('desc', None) != '操作成功':
				self._stop = True
				if self.METH not in self.EMAIL_SENT:
					self.EMAIL_SENT[self.METH] = 1
					send_mail('Shanghai Error!')
				assert False, f'Error in Shanghai! {res_json}'

		res_json, get_t = self._get_json(self.bus_url, is_post = True, json = self.bus_data, headers = SH_HEADERS, **kwargs)
		check_code(res_json)
		line_json, _ = self._get_json(self.line_url, is_post = True, json = self.line_data, headers = SH_HEADERS, **kwargs)
		check_code(line_json)

		line_json = line_json['data'][f'lineResults{self.direction}']
		assert line_json['direction'] == ('true' if self.direction == 0 else 'false'), 'Direction?'
		line_json = line_json['stop']
		res_json['_line'] = line_json

		return res_json, get_t

