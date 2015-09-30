# -*- coding: utf-8 -*-
# gasongjian@126.com
import re
import imaplib, email
import sys
import os  
import smtplib  
import mimetypes
import base64  
from email.MIMEMultipart import MIMEMultipart  
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText 
from email.encoders import encode_base64  
from email.header import Header
from email.utils import COMMASPACE,formatdate
from email import encoders

reload(sys)
sys.setdefaultencoding('utf8')

############################ Example:###################################
# import pymail
# from pymail import mail_send
# #初始化接收邮件类
# rml = pymail.ReceiveMail('mail_address','mail_pwd','imap.126.com')
# rml.select('INBOX')# 配合rml.showFolders()使用
# #获取需要的邮件列表('ALL','Unseen','Seen'等)
# items=rml.search(None,'All')
# #遍历邮件
# for num in items:
#    mailInfo=rml.mail_get(num)
#    #遍历附件列表
#    for attachment in mailInfo['attachments']:
#         fileob = open(attachment['name'],'wb')
#         fileob.write(attachment['data'])
#         fileob.close()
#         
#
#
# #初始化发送邮件类
#sml = pymail.SendMail('mail_address','mail_pwd','smtp.gmail.com')
##设置邮件信息
#sml.setMailInfo('paramiao@gmail.com','测试','正文','plain','/home/paramiao/resume.html')
##发送邮件
#sml.mail_send()
#
# #快速发送邮件
# mail_send(server,fro,to,subject,text,files)
#
#
#################################################################




#*********接受邮件部分（IMAP）**********
#处理接受邮件的类
class ReceiveMail:

    #构造函数(用户名，密码，imap服务器)
    def __init__(self, username, password, mailhost,port=993,ssl=1):
        if ssl==1:
            self.mail = imaplib.IMAP4_SSL(mailhost,port)
        else:
            self.mail = imaplib.IMAP4(mailhost, port)
        self.mail.login(username, password)
        self.select("INBOX")
        
    #返回邮箱的文件夹列表,已解决中文乱码问题
    #配合self.select()使用
    def showFolders(self):
        elist=self.mail.list()
        if elist[0]=='OK':
            elist=elist[1]
        else:
            elist=[]
            return elist
        for i,item in enumerate(elist):
            item=re.findall('"(.*?)"',item)
            item=item[1]
            s1=item
            if '&' in s1:
                s1=s1.replace('&','+')
                s1=s1.decode('utf7').encode('utf-8')
                item='"%s" / (%s)' %(item,s1)
                elist[i]=item
            else:
                item='"%s" / ()'% item
                elist[i]=item
        return elist
    
    #选择收件箱（如“INBOX”，如果不知道可以调用showFolders）
    def select(self, selector):
        return self.mail.select(selector)

    #搜索邮件(参照RFC文档http://tools.ietf.org/html/rfc3501#page-49)
    #'''
    #一般为：self.search(None,'ALL')
    #后者还有：'All,Unseen,Seen,Recent,Answered, Flagged'
    #'''
    def search(self, charset, *criteria):
        try:
            resp,items=self.mail.search(charset,*criteria)
            items=items[0].split()
            for i,item in enumerate(items):
                items[i]=int(item)
            return items    
        except :
            self.select("INBOX")
            resp,items=self.mail.search(charset,*criteria)
            items=items[0].split()
            for i,item in enumerate(items):
                itmes[i]=int(item)              
            return items

    #返回所有未读的邮件列表（返回的是包含邮件序号的列表）
    def getUnread(self):
        return self.search(None,"Unseen")
    
    #以RFC822协议格式返回邮件详情的email对象
    def getEmailFormat(self, num):
        data = self.mail.fetch(num, 'RFC822')
        if data[0] == 'OK':
            return email.message_from_string(data[1][0][1])
        else:
            return "fetch error"

    #返回发送者的信息——元组（邮件称呼，邮件地址）
    def getSenderInfo(self, msg):
        name = email.Utils.parseaddr(msg["from"])[0]
        deName = email.Header.decode_header(name)[0]
        if deName[1] != None:
            name = unicode(deName[0], deName[1])
        address = email.Utils.parseaddr(msg["from"])[1]
        return (name, address)

    #返回接受者的信息——元组（邮件称呼，邮件地址）
    def getReceiverInfo(self, msg):
        name = email.Utils.parseaddr(msg["to"])[0]
        deName = email.Header.decode_header(name)[0]
        if deName[1] != None:
            name = unicode(deName[0], deName[1])
        address = email.Utils.parseaddr(msg["to"])[1]
        return (name, address)

    #返回邮件的主题（参数msg是email对象，可调用getEmailFormat获得）
    def getSubjectContent(self, msg):
        deContent =  email.Header.decode_header(msg['subject'])[0]
        if deContent[1] != None:
            return unicode(deContent[0], deContent[1])
        return deContent[0]

    '''判断是否有附件，并解析（解析email对象的part）
    返回列表（内容类型，大小，文件名，数据流）
    '''
    def parse_attachment(self, message_part):
        content_disposition = message_part.get("Content-Disposition", None)
        if content_disposition:
            dispositions = content_disposition.strip().split(";")
            if bool(content_disposition and dispositions[0].lower() == "attachment"):

                file_data = message_part.get_payload(decode=True)
                attachment = {}
                attachment["content_type"] = message_part.get_content_type()
                attachment["size"] = len(file_data)
                deName = email.Header.decode_header(message_part.get_filename())[0]
                name = deName[0]
                if deName[1] != None:
                    name = unicode(deName[0], deName[1])
                name=name.replace('\r','')
                name=name.replace('\n','')
                print name
                attachment["name"] = name
                attachment["data"] = file_data
                # 保存附件到本地文件夹
                '''
                fileobject = open(name, "wb")
                fileobject.write(file_data)
                fileobject.close()
                '''
                return attachment
        return None

    '''返回邮件的解析后信息部分
    返回列表包含（主题，纯文本正文部分，html的正文部分，发件人元组，收件人元组，附件列表）
    '''
    def mail_get(self, num):
        ''' 返回单个邮件的相关信息,格式为dict
        from：发件人(格式tuple):(称呼,email)
        to：  收件人(格式tuple):(称呼,email)
        date: 邮件接收的时间
        subject：主题
        body,html:自定义邮件正文内容
        attachments:附件(list+dict),
        .dict:content_type,data,name,size
        '''
        msg = self.getEmailFormat(num)
        attachments = []
        body = None
        html = None
        for part in msg.walk():
            attachment = self.parse_attachment(part)
            if attachment:
                attachments.append(attachment)
            elif part.get_content_type() == "text/plain":
                if body is None:
                    body = ""
                bodytmp=part.get_payload(decode=True)
                body += bodytmp.decode('gbk').encode('utf-8')
            elif part.get_content_type() == "text/html":
                if html is None:
                    html = ""
                html += part.get_payload(decode=True)
        return {
            'subject' : self.getSubjectContent(msg),
            'body' : body,
            'html' : html,
            'from' : self.getSenderInfo(msg), 
            'to' : self.getReceiverInfo(msg), 
            'date':msg["Date"],
            'attachments': attachments,
        }



            


#*********发送邮件部分(smtp)**********
    
class SendMail:

    #构造函数（用户名，密码，smtp服务器）
    def __init__(self, user, passwd, smtp,port=25,usettls=False):
        self.mailUser = user  
        self.mailPassword = passwd
        self.smtpServer = smtp
        self.smtpPort   = port
        self.mailServer = smtplib.SMTP(self.smtpServer, self.smtpPort)  
        self.mailServer.ehlo()
        if usettls:		
            self.mailServer.starttls()  
        self.mailServer.ehlo()  
        self.mailServer.login(self.mailUser, self.mailPassword)
        self.msg = MIMEMultipart()

    #对象销毁时，关闭mailserver    
    def __del__(self):
        self.mailServer.close()

    #重新初始化邮件信息部分
    def reinitMailInfo():
        self.msg = MIMEMultipart()

    #设置邮件的基本信息（收件人，主题，正文，正文类型html或者plain，可变参数附件路径列表）
    def setMailInfo(self, receiveUser, subject, text, text_type,*attachmentFilePaths):    
        self.msg['From'] = self.mailUser  
        self.msg['To'] = receiveUser
        
        self.msg['Subject'] = subject  
        self.msg.attach(MIMEText(text, text_type))
        for attachmentFilePath in attachmentFilePaths:
            self.msg.attach(self.getAttachmentFromFile(attachmentFilePath))   

    #自定义邮件正文信息（正文内容，正文格式html或者plain）
    def addTextPart(self, text, text_type):
        self.msg.attach(MIMEText(text, text_type))
        

    #增加附件（以流形式添加，可以添加网络获取等流格式）参数（文件名，文件流）
    def addAttachment(self, filename, filedata):
        part = MIMEBase('application', "octet-stream")  
        part.set_payload(filedata)  
        encode_base64(part)  
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % str(Header(filename, 'utf8')))
        self.msg.attach(part)

    #通用方法添加邮件信息（MIMETEXT，MIMEIMAGE,MIMEBASE...）
    def addPart(self, part):
        self.msg.attach(part)

    # 发送邮件
    def mail_send(self):
        if not self.msg['To']:
            print "没有收件人,请先设置邮件基本信息"
            return 
        self.mailServer.sendmail(self.mailUser, self.msg['To'], self.msg.as_string())
        print('Sent email to %s' % self.msg['To'])  

    
    #通过路径添加附件
    def getAttachmentFromFile(self, attachmentFilePath):
        part = MIMEBase('application', "octet-stream")  
        part.set_payload(open(attachmentFilePath,"rb").read())  
        encode_base64(part)  
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % str(Header(attachmentFilePath, 'utf8')))   
        return part


'''备用函数
快捷的办法，没有自定义类
'''
def mail_send(server, fro, to, subject, text, files=[]): 
    '''
    #发送邮件函数
    server = {'name':'smtp.***.com', 'user':'***********', 'passwd':'********', 'port':25}
    fro = '**********'	
    to=['tomail1','tomail2']
    subject = u'测试邮件'
    text='powered by python'
    files=['file1.*']
    mail_send(server,fro,to,subject,text,files)
    '''
    assert type(server) == dict 
    assert type(to) == list 
    assert type(files) == list  
    msg = MIMEMultipart()
    msg['From'] = fro
    msg['Subject'] = Header(subject, 'gb2312') 
    #msg['Subject'] = subject 
    msg['To'] = COMMASPACE.join(to) #COMMASPACE==', ' 
    msg['Date'] = formatdate(localtime=True) 
    msg.attach(MIMEText(text,'plain','gb2312'))   
    for f in files: 
        att = MIMEText(open(f, 'rb').read(), 'base64', 'gb2312')
        filename = os.path.basename(f)
        att["Content-Type"] = 'application/octet-stream'
        att["Content-Disposition"] = 'attachment; filename=%s' % filename.encode('gb2312')
        msg.attach(att)   
    msg["Accept-Language"]="zh-CN"
    msg["Accept-Charset"]="ISO-8859-1,gb2312"    
    smtp = smtplib.SMTP(server['name'], server['port']) 	
    smtp.login(server['user'], server['passwd'])
    smtp.sendmail(fro, to, msg.as_string())   
    smtp.close()
    return
