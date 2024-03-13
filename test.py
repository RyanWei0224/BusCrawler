import os
import time
import json

ROUTE_DIR = 'routes'

def dict_del(d, k):
	if k in d:
		del d[k]
		return True
	return False


X = [
	'CZ_34',
	'CZ_517',
	'CZ_68',
	'CZ_88',
	'CZ_89',
	'CZ_B1',
	'CZ_K1',
	'JT_331',
	'NJ_34',
	'NJ_Y13',
	'NJ_Y14',
	'NJ_Y17',
	'NJ_Y1',
	'NJ_Y2',
	'NJ_Y34',
	'NJ_Y5',
	'NJ_Y8',
	'TC_123',
	'WX_26',
	'WX_26_2',
	'WX_G1',
	'WX_WT',
	'ZJ_302',
	'ZJ_302_2',
	'ZJ_606',
	'ZJ_633',
]

def clean_route():
	for fname in os.listdir(ROUTE_DIR):
		if not any(fname.startswith(i) for i in X):
			continue
		name = f'{ROUTE_DIR}/{fname}'
		with open(name, 'r', encoding = 'utf-8') as f:
			data = json.load(f)
		with open(name, 'r', encoding = 'utf-8') as f:
			data2 = json.load(f)

		dict_del(data, 'tip')
		dict_del(data, 'depDesc')
		dict_del(data, 'depTable')
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

		if data != data2:
			print('Here', fname)

		with open(name, 'w', encoding='utf-8') as f:
			json.dump(data, f, ensure_ascii = False, indent = '\t')

def print_diff(data1, data2, pref):
	if type(data1) != type(data2):
		print(f'{pref}: Diff type!')
		return

	if isinstance(data1, dict):
		for i in data1:
			if i not in data2:
				print(f'{pref}{i} only in A.')

		for i in data2:
			if i not in data1:
				print(f'{pref}{i} only in B.')

		for i in data1:
			if i not in data2:
				continue
			print_diff(data1[i], data2[i], f'{pref}/{i}')

		return

	if isinstance(data1, list):
		if len(data1) != len(data2):
			print(f'{pref}: Diff len!')
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
	datas = []
	maxt = -1
	for i in os.listdir(ROUTE_DIR):
		try:
			t = time.strptime(i, f'{name}_%y%m%d_%H%M%S_line.json')
		except ValueError:
			continue
		t = time.mktime(t)
		data = f'{ROUTE_DIR}/{i}'
		datas.append((t, data))

	datas.sort()

	first = True
	del_list = []

	for (_, d1), (_, d2) in zip(datas, datas[1:]):
		with open(d1, 'r', encoding = 'utf-8') as f:
			data1 = json.load(f)

		with open(d2, 'r', encoding = 'utf-8') as f:
			data2 = json.load(f)

		print('Diff:', d1, d2)
		print_diff(data1, data2, '')
		_=input()




def reset_route(name):
	datas = []
	maxt = -1
	for i in os.listdir(ROUTE_DIR):
		try:
			t = time.strptime(i, f'{name}_%y%m%d_%H%M%S_line.json')
		except ValueError:
			continue
		t = time.mktime(t)
		data = f'{ROUTE_DIR}/{i}'
		datas.append((t, data))

	datas.sort()

	first = True
	del_list = []

	for (_, d1), (_, d2) in zip(datas, datas[1:]):
		with open(d1, 'r', encoding = 'utf-8') as f:
			data1 = json.load(f)

		with open(d2, 'r', encoding = 'utf-8') as f:
			data2 = json.load(f)

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
	print(len(del_list))
	for i in del_list:
		os.remove(i)


if __name__ == '__main__':
	#clean_route()
	#for i in X:
	#	reset_route(i)
	#reset_route(input('Line:'))
	check_diff(input('Line:'))