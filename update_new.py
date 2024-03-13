import os
import pickle
from util import TPOINT_STR, PICKLE_DIR

def proc_bus(v):
	return sorted([(t, s, 0, None, None) for s, t in v.items()])

def proc_day(v):
	if '_last_dict' in v:
		del v['_last_dict']
	new_v = {k: proc_bus(d) for k, d in v.items()}
	s = set()
	for d in new_v.values():
		for l in d:
			s.add(l[0])
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

	fname = f'{PICKLE_DIR}/{name}.pickle'
	bak_name = f'{PICKLE_DIR}/{name}_merge_bak.pickle'
	has_old = os.path.isfile(fname)

	if has_old:
		with open(fname, 'rb') as f:
			cur_d = pickle.load(f)
		new_d = merge_dict(new_d, cur_d, max_depth = 0)

		import shutil
		shutil.copy2(fname, bak_name)

	with open(fname, 'wb') as f:
		pickle.dump(new_d, f)

	if has_old:
		os.remove(bak_name)


with open('all.pickle', 'rb') as f:
	x = pickle.load(f)

for k, v in x.items():
	proc_route(k, v)
