import pickle
from util import TPOINT_STR

def proc_bus(v):
	return sorted([(t, s, 0, None, None) for s, t in v.items()])

def proc_day(v):
	if '_last_dict' in v:
		del v['_last_dict']
	new_v = {k:proc_bus(d) for k, d in v.items()}
	s = set()
	for d in new_v.values():
		for d2, _ in d:
			s.add(d2)
	s = sorted(s)
	new_v[TPOINT_STR] = s
	return new_v

def proc_route(name, d):
	if 'method' in d:
		del d['method']
	new_d = dict()
	for k in sorted(d.keys()):
		v = proc_day(d[k])
		new_d[k] = v
	with open(f'pickle_test/{name}.pickle', 'wb') as f:
		pickle.dump(d, f)

with open('all.pickle', 'rb') as f:
	x = pickle.load(f)

for k, v in x.items():
	proc_route(k, v)
