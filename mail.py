import smtplib
from email.mime.text import MIMEText
import time

from config import mail_host, mail_user, mail_pass, sender, receivers


next_t = -1

def send_mail(s, subject = '高德'):
	global next_t
	#设置email信息
	#邮件内容设置
	message = MIMEText(s,'plain','utf-8')
	#邮件主题
	message['Subject'] = subject
	#发送方信息
	message['From'] = sender
	#接受方信息     
	message['To'] = receivers[0]

	next_t -= time.time()
	if next_t > 0:
		time.sleep(next_t)
	next_t = time.time() + 60

	#登录并发送邮件
	try:
		'''
		smtpObj = smtplib.SMTP() 
		#连接到服务器
		smtpObj.connect(mail_host,25)
		#登录到服务器
		'''
		smtpObj = smtplib.SMTP_SSL(mail_host)
		smtpObj.login(mail_user,mail_pass) 
		#发送
		smtpObj.sendmail(
			sender,receivers,message.as_string()) 
		#退出
		smtpObj.quit()
	except smtplib.SMTPException as e:
		print('Mail Error')
		print(e) #打印错误