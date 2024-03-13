
SH_TOKEN = ''
KS_TOKEN = ''
TC_TOKEN = ''

SH_HEADERS = {
	'Host': 'smartgate.ywtbsupappw.sh.gov.cn',
#	'Authentication': SH_TOKEN,
	# ...
}

SH_DATA = {
	'userSystemData': {
		'brand':'microsoft',
		# ...
	},
	'sessionId': SH_TOKEN,
}

ZSCX_HEADERS = {
	'Host': 'wx.mygolbs.com',
	'Connection': 'keep-alive',
	# ...
}

WX_TOK_JSON = {
	'accessId': '',
	'accessSecret': '',
}

SZ_TOKEN = ''

CLL_SIGN = ''

# For mail

#设置服务器所需信息
#邮箱服务器地址
mail_host = 'smtp.qq.com'
#用户名
mail_user = ''
#密码(部分邮箱为授权码) 
mail_pass = ''
#邮件发送方邮箱地址
sender = '@qq.com'
#邮件接受方邮箱地址，注意需要[]包裹，这意味着你可以写多个邮件地址群发
receivers = ['@qq.com']

