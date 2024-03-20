from threading import Thread as Worker
import time

from crawlers.all import ALL_CRAWLERS
from util import sleep_intr, print_log, CT, cur_time

INTV = 19
PING_INTV = 60


def get_req(crawler, endt = None, stop_l = [], get_line = False, update = True):
	tries = 0
	intv = 3
	timeout = 6.1
	while not (stop_l or (endt is not None and cur_time() >= endt)):
		try:
			# t = time.time()
			tries += 1
			res_json, get_t = crawler.get_once(get_line = get_line, timeout = timeout)
		except Exception as e:
			# DEBUG: raise e
			if crawler.stop():
				raise e

			err_str = f'Error "{e}" at {crawler.name()}'
			print_log(err_str, verbose = get_line)

			if '429 Client Error: Too Many Requests' in str(e):
				sleep_intr(30, stop_l)
				continue

			if timeout < 12 and 'Read timed out' in str(e):
				timeout += 3.05

			'''
			t = (t + intv) - time.time()
			if t > 0:
				sleep_intr(t, stop_l)
			'''
			sleep_intr(intv, stop_l)

			if intv < 20 and tries >= 3:
				intv += 2

			continue

		if res_json is None or not update:
			break

		try:
			func = crawler.update_route if get_line else crawler.proc_update
			func(res_json, get_t)
		except Exception as e:
			print_log(f'Exception at proc {crawler.name()}: {e}', verbose = True)

		break

	return


def line_thread(crawler, endt, stop_l, update = True, intv = INTV):
	try:
		import random
		while not (stop_l or (endt is not None and cur_time() >= endt)):
			t0 = time.time()
			t = t0 + intv + random.uniform(-3, 3)
			try:
				get_req(crawler, endt = endt, stop_l = stop_l, update = update)
			except Exception as e:
				print_log(f'At line {crawler.name()}: {e} of {type(e)}', verbose = True)
				return
			t0 = time.time() - t0
			print_log(f'Delay: {t0:.2f}s. {crawler.name()}')
			t = t - time.time()
			if t > 0:
				sleep_intr(t, stop_l)
	except KeyboardInterrupt:
		return


def update_routes(lines):
	print('Update routes...')

	all_meths = [meth for meth, Crawler in ALL_CRAWLERS.items() if Crawler.GET_LINE]

	for name, line in lines.items():
		meth = line[-1]
		line_info = line[0]
		if meth not in all_meths:
			continue

		try:
			crawler = ALL_CRAWLERS[meth](name, line_info)
			if crawler.stop():
				print_log(f'At update_routes: skipping {name}', verbose = True)
				continue
			get_req(crawler, get_line = True)
		except Exception as e:
			print(type(e), e, name, "at update_routes")

	print('Finished')


def ping_thread(lines, stop_l):
	thrs = []
	for k, v in lines.items():
		crawler = ALL_CRAWLERS[v[-1]](k, v[0])
		if crawler.stop():
			print_log(f'At ping: skipping {k}', verbose = True)
			continue
		thr = Worker(target = line_thread, args = (crawler, None, stop_l), kwargs = {'update': False, 'intv': PING_INTV})
		thrs.append(thr)

	for i in thrs:
		i.start()
		sleep_intr(3, stop_l)
	for i in thrs:
		i.join()
	return


def check_lines(l):
	def proc(v):
		if not isinstance(v, (list, dict)):
			return v
		if isinstance(v, dict):
			v = [(a, b) for a, b in v.items()]
		v = tuple(proc(i) for i in v)
		return v

	urls = dict()
	for name in l:
		if name in ['SZR_106M_2', 'TCR_308Y_2', 'TC_308Y_2', 'TCR_308Z_2', 'TC_308Z_2', 'CZR_89R', 'CZR_89_2R']:
			continue
		var = l[name]
		url = (proc(var[0]), var[-1])
		if url in urls:
			print(f'Find same route! {urls[url]} = {name}')
			return False
		urls[url] = name
	return True


def main(l, pl):
	assert check_lines(l)

	from util import init
	init()

	stop_l = []
	running = dict()
	finished = set()
	ping_pong = True

	try:
		ping_thr = Worker(target = ping_thread, args = (pl, stop_l))
		ping_thr.start()

		while True:
			time.sleep(2)

			# Join workers
			join_procs = []
			for k, v in running.items():
				if not v.is_alive():
					v.join()
					join_procs.append(k)
			for k in join_procs:
				del running[k]
				finished.add(k)

			# Start workers
			for bus_name in l.keys():
				if bus_name in finished:
					continue
				line_info, startt, endt, meth = l[bus_name]
				ct = cur_time()
				if bus_name not in running and startt <= ct and ct < endt:
					crawler = ALL_CRAWLERS[meth](bus_name, line_info)
					# Test if crawler not available
					if crawler.stop():
						print_log(f'Skipping {bus_name}', verbose = True)
						finished.add(bus_name)
					else:
						thr = Worker(target = line_thread, args = (crawler, endt, stop_l))
						running[bus_name] = thr
						thr.start()
						time.sleep(2)

			# Update between 0:00 and 2:00
			ct = cur_time()
			if ping_pong and ct <= CT(2, 0): # and ct >= CT(0, 0)
				update_routes(l)
				finished.clear()
				ping_pong = False
			elif (not ping_pong) and ct > CT(6, 0):
				ping_pong = True

	except KeyboardInterrupt:
		print('Ctrl-C detected. Stopping...')
		pass

	stop_l.append(True)
	for i in running:
		running[i].join()
	ping_thr.join()


if __name__ == '__main__':
	from lines import LINES, PING_LINES
	main(LINES, PING_LINES)
	# update_routes(LINES)

