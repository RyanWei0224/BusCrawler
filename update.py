from bus import update_routes
from lines import LINES


def main():
	update_routes(LINES)
	print('OK')
	_=input()

if __name__ == '__main__':
	main()
