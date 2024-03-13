from .base import CrawlerBase


class Changshu(CrawlerBase):
	METH = 7
	GET_LINE = True
	def __init__(self, bus_name, line_info):
		super().__init__(bus_name, line_info)
		liguid, lbguid, ismain = line_info
		if isinstance(liguid, str):
			assert len(liguid) == 36, f'Wrong format of liguid: {liguid}'
		else:
			lineId, upDown = liguid
			liguid = f'{lineId:{upDown}>36d}'
		self.bus_url   = f'https://www.csxapi.cn/busdata/{liguid}/buses'
		self.line_url  =  'https://www.csxapi.cn/app/nearby/detailStandsByLbguid'
		self.line_data = {
			'liguid': liguid,
			'lbguid': '1',
			'ismain': ismain,
		}


	def get_stations(self, line_json):
		stations = [s['sname'] for s in line_json['list']]
		return stations


	# 13, 0 : 13 -> 14
	# 13, 1 : at 13
	def proc(self, res_json):
		def _proc(bus_data):
			in_station = 0
			lon = bus_data.get('slon', None)
			lat = bus_data.get('slat', None)
			return (bus_data['dbuscard'], bus_data['slno'] - 1, in_station, lon, lat)

		bus_datas = [_proc(i) for i in res_json['content']]
		return bus_datas, None


	def _get_once(self, get_line = False, **kwargs):
		if get_line:
			res_json, get_t = super()._get_json(self.line_url, is_post = True, json = self.line_data)
			if res_json['msg'] != '数据取得成功！' or res_json['succ'] is not True:
				assert False, f'Failed! msg: {res_json["msg"]}, succ: {res_json["succ"]}'
			res_json = res_json['dataObj']
			for d in res_json['list']:
				del d['lbguid']
		else:
			res_json, get_t = super()._get_json(self.bus_url)
			if res_json['type'] != 'response' or res_json['status'] != '200':
				assert False, f'Failed! type: {res_json["type"]}, status: {res_json["status"]}'

		return res_json, get_t

