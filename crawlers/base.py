import json
import os
import pickle
import requests
import time
from lxml import etree

from .util import TPOINT_STR, PICKLE_DIR, ROUTE_DIR
from .util import merge_dict, dict_empty


class CrawlerBase:
	EMAIL_SENT = dict()
	TIMEOUT = 600
	# METH = None
	# GET_LINE = None
	def __init__(self, bus_name, line_info):
		self.bus_name = bus_name
		self.bus_dict = dict()
		self.line_url = None
		self.bus_url = None

		self.file_name = f'{PICKLE_DIR}/{self.bus_name}.pickle'
		self.bak_name = f'{PICKLE_DIR}/{self.bus_name}_bak.pickle'

		self.line_json = self.load_line()
		self._stop = False
		self.flush_time = time.time() + self.TIMEOUT


	def get_stations(self, line_json):
		raise NotImplementedError
		# return ['station1', 'station2', ...]


	# 13, 0 : 13 -> 14
	# 13, 1 : at 13
	def proc(self, res_json):
		raise NotImplementedError
		# bus_datas: [(bus_id, station_id, in_station)]
		# return bus_datas, line_json


	def _get_once(self, get_line = False, **kwargs):
		url = self.line_url if get_line else self.bus_url
		res_json, get_t = self._get_json(url, **kwargs)
		return res_json, get_t




	def _get_req(self, url, is_post = False, timeout = 3.05, **kwargs):
		func = requests.post if is_post else requests.get
		res = func(url, timeout = timeout, **kwargs)
		get_t = time.localtime()
		res.raise_for_status()
		return res, get_t


	def _get_json(self, url, **kwargs):
		res, get_t = self._get_req(url, **kwargs)
		res_json = res.json()
		return res_json, get_t


	def _get_html(self, url, **kwargs):
		res, get_t = self._get_req(url, **kwargs)
		res_html = etree.fromstring(res.content, etree.XMLParser())
		return res_html, get_t


	def get_once(self, get_line = False, **kwargs):
		if not self.GET_LINE:
			assert not get_line, 'No need to get line!'
		self.check_save()
		res_json, get_t = self._get_once(get_line = get_line, **kwargs)
		return res_json, get_t


	def check_save(self):
		if time.time() < self.flush_time:
			return

		self.save()
		self.flush_time = time.time() + self.TIMEOUT


	def load_line(self):
		line_file = None
		maxt = -1
		for i in os.listdir(ROUTE_DIR):
			try:
				t = time.strptime(i, f'{self.bus_name}_%y%m%d_%H%M%S_line.json')
			except ValueError:
				continue
			t = time.mktime(t)
			if t <= maxt:
				continue
			maxt = t
			line_file = f'{ROUTE_DIR}/{i}'
			
		if line_file is None:
			return None

		with open(line_file, 'r', encoding = 'utf-8') as f:
			data = json.load(f)
		return data


	def update(self, bus_datas, get_t):
		day = time.strftime('%y/%m/%d', get_t)
		if day not in self.bus_dict:
			self.bus_dict[day] = dict()
		cur_dict = self.bus_dict[day]

		daytime = (get_t.tm_hour * 60 + get_t.tm_min) * 60 + get_t.tm_sec

		for bus_id, station_id, in_station, lon, lat in bus_datas:
			assert station_id >= 0 and in_station in (0, 1), f'Illegal state ({station_id}, {in_station})'

			if bus_id not in cur_dict:
				cur_dict[bus_id] = list()

			cur_dict[bus_id].append((daytime, station_id, in_station, lon, lat))

		if TPOINT_STR not in cur_dict:
			cur_dict[TPOINT_STR] = list()
		cur_dict[TPOINT_STR].append(daytime)

		self.check_save()


	def update_route(self, line_json, get_t):
		if line_json is None or line_json == self.line_json:
			return

		self.line_json = line_json

		line_file = time.strftime(f'{ROUTE_DIR}/{self.bus_name}_%y%m%d_%H%M%S_line.json', get_t)
		assert not os.path.isfile(line_file), f'File {line_file} already exists!'

		with open(line_file, 'w', encoding = 'utf-8') as f:
			json.dump(line_json, f, ensure_ascii = False, indent = '\t')

		print('New route info:', line_file)


	def proc_update(self, res_json, get_t):
		bus_datas, line_json = self.proc(res_json)
		self.update(bus_datas, get_t)
		self.update_route(line_json, get_t)


	def save(self):
		if dict_empty(self.bus_dict):
			return False

		if os.path.isfile(self.file_name):
			with open(self.file_name, 'rb') as f:
				d = pickle.load(f)
			self.bus_dict = merge_dict(d, self.bus_dict)

			import shutil
			shutil.copy2(self.file_name, self.bak_name)

		with open(self.file_name, 'wb') as f:
			pickle.dump(self.bus_dict, f)
		# os.remove(self.bak_name)
		self.bus_dict.clear()
		return True


	def stop(self):
		return self._stop


	def name(self):
		return self.bus_name


	def __del__(self):
		self.save()

