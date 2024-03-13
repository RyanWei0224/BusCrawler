from .base import CrawlerBase


class Jiading(CrawlerBase):
	METH = 9
	GET_LINE = False
	def __init__(self, bus_name, line_info):
		super().__init__(bus_name, line_info)
		lineId, upDown = line_info
		self.bus_url  = f'https://wx.jd-bus.com:1443/api/carMonitor_new?my=aa&t=bb&lineid={lineId}&direction={upDown}'
		self.line_url = f'https://wx.jd-bus.com:1443/api/getAllLdly?my=aa&t=bb&lineid={lineId}'
		self.sch_url  = f'https://wx.jd-bus.com:1443/api/line_schedule?my=aa&t=bb&lineid={lineId}&direction={upDown}'
		self.upDown   = 'false' if upDown == 1 else 'true'


	@classmethod
	def get_stations(cls, line_json):
		def _proc(s):
			try:
				lon = float(s['SOURCE_LON'])
			except Exception:
				lon = None
			try:
				lat = float(s['SOURCE_LAT'])
			except Exception:
				lat = None
			return (s['ZDMC'], lon, lat)
		stations = [_proc(s) for s in line_json['line']]
		return stations


	# 13, 0 : 13 -> 14
	# 13, 1 : at 13
	def proc(self, res_json):
		def _proc(bus_data, tot_stop):
			rem_stop = int(bus_data['stopdis'])
			cur_stop = (tot_stop - 1) - rem_stop
			try:
				lon = float(bus_data['lon'])
			except Exception:
				lon = None
			try:
				lat = float(bus_data['lat'])
			except Exception:
				lat = None
			return (bus_data['terminal'], cur_stop, int(bus_data['inout']), lon, lat)

		line_json = res_json['_line']
		tot_stop  = len(line_json['line'])
		bus_datas = [_proc(i, tot_stop) for i in res_json['data']]

		from util import dict_del
		for i in line_json['sch']:
			dict_del(i, 'id')
			dict_del(i, 'scheduleDateStr')
			dict_del(i, 'nbbm')
			dict_del(i, 'jsy')

		return bus_datas, line_json


	def _get_once(self, get_line = False, **kwargs):
		res_html, get_t = self._get_html(self.bus_url, is_post = True, **kwargs)
		res_html = res_html[0]
		def proc_xml(elem):
			return {i.tag: i.text for i in elem}
		res_json = {'data': [proc_xml(elem) for elem in res_html]}

		line_json, _ = self._get_json(self.line_url, is_post = True, **kwargs)
		line_json = line_json['zdly'][self.upDown]
		sch_json, _ = self._get_json(self.sch_url, is_post = True, **kwargs)

		res_json['_line'] = {
			'line': line_json,
			'sch' : sch_json,
		}

		return res_json, get_t

