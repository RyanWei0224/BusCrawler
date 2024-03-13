from .changshu import Changshu
from .changzhou import Changzhou
from .chelaile import Chelaile
from .danyang import Danyang
from .jiading import Jiading
from .kunshan import Kunshan
from .shanghai import Shanghai
from .suzhou import Suzhou
from .taicang import Taicang
from .wuxi import Wuxi
from .zhangjiagang import Zhangjiagang
from .zscx import ZSCX

'''
method:
0: cll
1: dy
2: zscx
3: czx
4: wx
5: sz
6: ks
7: cs
8: zjg
9: jd
10: sh
11: tc
'''

ALL_CRAWLERS = [
	Changshu,
	Changzhou,
	Chelaile,
	Danyang,
	Jiading,
	Kunshan,
	Shanghai,
	Suzhou,
	Taicang,
	Wuxi,
	Zhangjiagang,
	ZSCX,
]
ALL_CRAWLERS.sort(key = lambda x: x.METH)
assert all(i.METH != j.METH for i, j in zip(ALL_CRAWLERS, ALL_CRAWLERS[1:]))
ALL_CRAWLERS = {i.METH: i for i in ALL_CRAWLERS}