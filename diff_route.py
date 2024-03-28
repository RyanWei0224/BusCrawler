import os
import json
import re

from lines import LINES
from util import ROUTE_DIR, dict_del
from util import LINE_JSON_RE, ljson_files, ljson_allfs, load_json

MAXL = 500


def clean_route():
	for fname in os.listdir(ROUTE_DIR):
		res = re.fullmatch(LINE_JSON_RE, fname)
		assert res is not None, f'Cannot match "{fname}"'
		bus_name = res[1]
		if bus_name not in LINES:
			print(f'[Warning] {bus_name} not found!')
			continue
		meth = LINES[bus_name][-1]
		if meth not in []: # [0, 9]:
			continue

		name = f'{ROUTE_DIR}/{fname}'
		data = load_json(name)
		data2 = load_json(name)

		if meth == 0:
			dict_del(data, 'tip')
			dict_del(data, 'depDesc')
			dict_del(data, 'depTable')
			dict_del(data['line'], 'afterEndOperatingTimeHalfHour')
			dict_del(data['line'], 'desc')
			dict_del(data['line'], 'ksDesc')
			dict_del(data['line'], 'shortDesc')
			dict_del(data['line'], 'state')
			dict_del(data['line'], 'assistDesc')
			dict_del(data['line'], 'nextOperationTimeDesc')
			dict_del(data['line'], 'ksAssistDesc')
			dict_del(data['line'], 'lineDisplayTags')
			dict_del(data['line'], 'lineDisplayTags')
			dict_del(data, 'roads')
			dict_del(data, 'preArrivalTime')
			dict_del(data, 'predictionLink')
			dict_del(data, 'predictionText')
			dict_del(data, 'nearStnOrder')
			dict_del(data, 'targetOrder')
		elif meth == 9:
			for i in data['sch']:
				dict_del(i, 'id')
				dict_del(i, 'scheduleDateStr')
				dict_del(i, 'nbbm')
				dict_del(i, 'jsy')

		if data != data2:
			print('Here', fname)

		with open(name, 'w', encoding='utf-8') as f:
			json.dump(data, f, ensure_ascii = False, indent = '\t')


def print_obj(obj, **kwargs):
	if isinstance(obj, dict):
		if 'stationName' in obj:
			print(obj['stationName'], **kwargs)
			return
		if 'fcsj' in obj:
			print(obj['fcsj'], **kwargs)
			return

	x = str(obj)
	if len(x) > MAXL:
		x = x[:MAXL-3] + '...'
	print(x, **kwargs)


def print_diff(data1, data2, pref):
	if type(data1) != type(data2):
		print(f'{pref}: Diff type!')
		return

	if isinstance(data1, dict):
		for i in data1:
			if i not in data2:
				print(f'{pref}[{i}] only in A, {pref}[{i}]:')
				print_obj(data1[i])


		for i in data2:
			if i not in data1:
				print(f'{pref}[{i}] only in B, {pref}[{i}]:')
				print_obj(data2[i])

		for i in data1:
			if i not in data2:
				continue
			if i == 'jxPath':
				continue
			print_diff(data1[i], data2[i], f'{pref}[{i}]')

		return

	if isinstance(data1, list):
		if all(isinstance(i, dict) for i in data1) and all(isinstance(i, dict) for i in data2):
			#if len(data1) != len(data2):
			#	print(f'{pref}: Diff len! {len(data1)} -> {len(data2)}')
			def find_key(l, st):
				if not l:
					return set()
				return {k for k in l[0].keys() if all(str(i.get(k, None)) == str(st+num) for num, i in enumerate(l))}

			k0 = find_key(data1, 0) & find_key(data2, 0)
			k1 = find_key(data1, 1) & find_key(data2, 1)
			keys = k0 | k1

			def all_in(key):
				return all(key in i for i in data1) and all(key in i for i in data2)

			serial_print = False

			if all_in('createTime'):
				keys.add('createTime')
				keys.add('id')
				keys.add('byStartDistance')
				serial_print = True
			elif all_in('lpName'):
				keys.add('lpName')
				serial_print = True
			elif all_in('namesakeStId') and all_in('distanceToSp'):
				keys.add('namesakeStId')
				keys.add('distanceToSp')

			def remove_keys(l, keys):
				if not keys:
					return l
				l = [i.copy() for i in l]
				for i in l:
					for k in keys:
						del i[k]
				return l

			rem_data1 = remove_keys(data1, keys)
			rem_data2 = remove_keys(data2, keys)

			a_list = []
			b_list = []
			st = 0

			def a_del(i):
				if serial_print:
					a_list.append(data1[i])
				else:
					print(f'{pref}[{i}] in A is deleted:', end = '')
					print_obj(data1[i])

			def b_add(j):
				if serial_print:
					b_list.append(data2[j])
				else:
					print(f'{pref}[{j}] in B is added:', end = '')
					print_obj(data2[j])

			for i, x in enumerate(rem_data1):
				try:
					cur = rem_data2.index(x, st)
				except ValueError:
					a_del(i)
				else:
					for j in range(st, cur):
						b_add(j)
					st = cur+1

			for j in range(st, len(data2)):
				b_add(j)

			def output(l, s):
				if not l:
					return
				print(s, end = '')
				for i in l[:-1]:
					print_obj(i, end = ',')
				print_obj(l[-1])

			output(a_list, f'{pref} in A is deleted:')
			output(b_list, f'{pref} in B is added:')
			return

		num = 0
		for i, j in zip(data1, data2):
			print_diff(i, j, f'{pref}[{num}]')
			num += 1

		return

	if data1 != data2:
		print(f'{pref}: different:')
		print(f'\t"{data1}"')
		print(f'\t"{data2}"')


def check_diff(name):
	datas = ljson_files(name)

	first = True
	del_list = []

	for (_, d1), (_, d2) in zip(datas, datas[1:]):
		data1 = load_json(d1)
		data2 = load_json(d2)

		print('Diff:', d1, d2)
		print_diff(data1, data2, '')
		_=input()


def list_diff():
	data_dict = ljson_allfs()

	datas = []
	for l in data_dict.values():
		l.sort()
		datas += [(t2, d1, d2) for (t1, d1), (t2, d2) in zip(l, l[1:])]

	datas.sort(reverse = True)

	for (_, d1, d2) in datas:
		data1 = load_json(d1)
		data2 = load_json(d2)

		print('Diff:', d1, d2)
		print_diff(data1, data2, '')
		_=input()


def reset_route(name):
	datas = ljson_files(name)

	first = True
	del_list = []

	for (_, d1), (_, d2) in zip(datas, datas[1:]):
		data1 = load_json(d1)
		data2 = load_json(d2)

		if data2 == data1:
			del_list.append(d2)
		'''
		del11 = dict_del(data1, 'predictionLink')
		del12 = dict_del(data1, 'predictionText')
		del21 = dict_del(data2, 'predictionLink')
		del22 = dict_del(data2, 'predictionText')

		if data2 == data1:
			print(d2, del11, del12, del21, del22)
			if first:
				assert not (del11 or del12)
			first = False
			del_list.append(d2)
		else:
			if set(data1.keys()) != set(data2.keys()):
				print(d1, d2)
				print(set(data1.keys()) - set(data2.keys()), set(data2.keys()) - set(data1.keys()))
				_=input()
			else:
				print(d1, d2)
				for i in data1:
					if data1[i] != data2[i]:
						print(i)
				_=input()
		'''

	# assert not (del21 or del22)
	if del_list:
		print(len(del_list))
	for i in del_list:
		os.remove(i)


def reset_route_all():
	names = set()
	for i in os.listdir(ROUTE_DIR):
		res = re.fullmatch(LINE_JSON_RE, i)
		if res is None:
			continue
		name = res[1]
		names.add(name)
	for name in names:
		reset_route(name)


def main():
	clean_route()
	reset_route_all()
	#for i in X:
	#	reset_route(i)
	#reset_route(input('Line:'))
	#check_diff(input('Line:'))
	list_diff()


if __name__ == '__main__':
	main()

