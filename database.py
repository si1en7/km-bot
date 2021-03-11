import mysql.connector
import datetime
from dotenv import load_dotenv
import os
import sys
load_dotenv()

class KMDB:
    def __init__(self):
        self.db = mysql.connector.connect(
            host=os.getenv('DBHOST'),
            user=os.getenv('DBUSER'),
            password=os.getenv('DBPASS'),
            database=os.getenv('DB')
        )
    def checkduplicate(self,data,table):
        cursor = self.db.cursor(dictionary=True)
        sql = f'SELECT * FROM {table} WHERE name="{data["name"]}" AND isk="{data["isk"]}" '
        count = cursor.execute(sql)
        cursor.fetchall()
        return cursor.rowcount

    def checkchannels(self,guild):
        cursor = self.db.cursor(dictionary=True)
        sql = f'SELECT * FROM guilds WHERE guild_id="{guild}"'
        cursor.execute(sql)
        row = cursor.fetchone()
        return (row['losschannel'], row['killchannel'], row['fixchannel'])

    def checkroles(self,guild):
        cursor = self.db.cursor(dictionary=True)
        sql = f'SELECT roles FROM guilds WHERE guild_id="{guild}"'
        cursor.execute(sql)
        row = cursor.fetchone()
        return (row['roles'])

    def checkdebug(self,guild):
        cursor = self.db.cursor(dictionary=True)
        sql = f'SELECT debug FROM guilds WHERE guild_id="{guild}"'
        cursor.execute(sql)
        row = cursor.fetchone()
        return row['debug']
    def checkreactions(self,guild):
        cursor = self.db.cursor(dictionary=True)
        sql = f'SELECT reactions FROM guilds WHERE guild_id="{guild}"'
        cursor.execute(sql)
        row = cursor.fetchone()
        return row['reactions']
    def toggledebug(self,guild):
        cursor = self.db.cursor(dictionary=True)
        if self.checkdebug(guild) == 1:
            sql = f'UPDATE guilds set debug="0" WHERE guild_id="{guild}"'
            response = "Debugging output has been **disabled.**"
        if self.checkdebug(guild) == 0:
            sql = f'UPDATE guilds set debug="1" WHERE guild_id="{guild}"'
            response = "Debugging output has been **enabled.**"
        cursor.execute(sql)
        self.db.commit()
        return response
    def insertkm(self,data,table):
        col = []
        values = []
        for key,value in data.items():
            values.append(value)
            col.append(key)
        cursor = self.db.cursor()
        cols = str(col)[1:-1]
        cols = cols.replace("'","")
        sql = f'INSERT INTO {table} ({cols}) VALUES ({str(values)[1:-1]})'
        #print(sql)
        cursor.execute(sql)
        self.db.commit()
    def assignkm(self,gid,id=0):
        cursor = self.db.cursor(dictionary=True,buffered=True)
        if id == 0:
            
            sql = f'SELECT currentfix FROM guilds WHERE guild_id="{gid}"'
            cursor.execute(sql)
            row = cursor.fetchone()
            if row['currentfix'] == "0":
                return 0
            else:
                return row['currentfix']
        else:  
            sql = f'UPDATE guilds set currentfix="{id}" WHERE guild_id="{gid}"'
            cursor.execute(sql)
            self.db.commit()
    def fixkm(self,gid):
        self.db.commit()
        cursor = self.db.cursor(dictionary=True,buffered=True)
        idresult = self.assignkm(gid)
        if idresult != 0:
            sql = f'SELECT * from killmail_fix where id="{idresult}"'
            cursor.execute(sql)
            row = cursor.fetchone()
            return row
        else:
            sql = f'SELECT * from killmail_fix WHERE guild_id="{gid}"'
            cursor.execute(sql)
            row = cursor.fetchone()
            if row:
                print(row['id'])
                self.assignkm(gid,row['id'])
                return row
        return False

    def fixfield(self,gid,field,value):
        cursor = self.db.cursor(dictionary=True)
        idresult = self.assignkm(gid)
        if idresult != 0:
            sql = f'UPDATE killmail_fix set {field}="{value}" WHERE id="{idresult}"'
            try:
                cursor.execute(sql)
                self.db.commit()
            except (mysql.connector.Error, mysql.connector.Warning) as e:
                print(e)
                return 0
        return 1
    def closekm(self,gid):
        cursor = self.db.cursor(dictionary=True)
        idresult = self.assignkm(gid)
        if idresult != 0:
            sql = f'INSERT into killmail (message_id,guild_id,name,playerid,isk,time,playership,kmtype,participants,finalblow,location,errors,filename) SELECT message_id,guild_id,name,playerid,isk,time,playership,kmtype,participants,finalblow,location,errors,filename FROM killmail_fix WHERE id="{idresult}"'
            try:
                cursor.execute(sql)
                self.db.commit()
            except (mysql.connector.Error, mysql.connector.Warning) as e:
                print(e)
                return False
            sql = f'DELETE FROM killmail_fix WHERE id="{idresult}"'
            try:
                cursor.execute(sql)
                self.db.commit()
            except (mysql.connector.Error, mysql.connector.Warning) as e:
                print(e)
                return False
            sql = f'UPDATE guilds SET currentfix="0" WHERE guild_id="{gid}"'
            try:
                cursor.execute(sql)
                self.db.commit()
            except (mysql.connector.Error, mysql.connector.Warning) as e:
                print(e)
                return False
        self.db.commit()
        return True
            

            
    def getbymid(self,mid):
        cursor = self.db.cursor(dictionary=True)
        sql = f'SELECT * FROM killmail WHERE message_id={mid}'
        cursor.execute(sql)
        rows = cursor.fetchall()
        if not rows:
            sql = f'SELECT * FROM killmail_fix WHERE message_id={mid}'
            cursor.execute(sql)
            rows = cursor.fetchall()
        return rows

    def getiskdaily(self):
        cursor = self.db.cursor(dictionary=True)
        currentdate = datetime.datetime.now()
        currentdate = currentdate.strftime("%Y-%m-%d 00:00:00")
        sql = f'SELECT isk FROM killmail WHERE time>="{currentdate}"'
        cursor.execute(sql)
        rows = cursor.fetchall()
        total = 0
        
        for row in rows:
            if row['isk'] != None:
                total = total + int(row["isk"])
        return(f'24-hour ISK Total **Ƶ {total:,}**')

    def getiskday(self,day,type):
            cursor = self.db.cursor(dictionary=True)
            if day == "now":
                searchdate = datetime.datetime.now()
                justday = searchdate.strftime("%Y/%m/%d")
                starttime = searchdate.strftime("%Y-%m-%d 00:00:00")
                endtime = searchdate.strftime("%Y-%m-%d 23:59:59")
                
            else:
                
                splitdate = day.split("/")
                searchdate = datetime.datetime(int(splitdate[0]),int(splitdate[1]),int(splitdate[2]))
                justday = searchdate.strftime("%Y/%m/%d")
                starttime = searchdate.strftime("%Y-%m-%d 00:00:00")
                endtime = searchdate.strftime("%Y-%m-%d 23:59:59")
                
            sql = f'SELECT isk FROM killmail WHERE time BETWEEN "{starttime}" AND "{endtime}" AND kmtype="{type}"'
            cursor.execute(sql)
            rows = cursor.fetchall()
            total = 0
                
            for row in rows:
                if row['isk'] != None:
                    total = total + int(row["isk"])
            return(f'ISK {type.lower()} Total for {justday}: **Ƶ {total:,}**')
    def getiskrange(self,dayleft,dayright,type):
            cursor = self.db.cursor(dictionary=True)
            
        
            dayleft = dayleft.split("/")
            dayright = dayright.split("/")
            firstday = datetime.datetime(int(dayleft[0]),int(dayleft[1]),int(dayleft[2]))
            lastday = datetime.datetime(int(dayright[0]),int(dayright[1]),int(dayright[2]))
            justdayleft = firstday.strftime("%Y/%m/%d")
            justdayright = lastday.strftime("%Y/%m/%d")
            if int(dayleft[1]) > int(dayright[1]):
                return 99
            starttime = firstday.strftime("%Y-%m-%d 00:00:00")
            endtime = lastday.strftime("%Y-%m-%d 23:59:59")
            
            sql = f'SELECT isk FROM killmail WHERE time BETWEEN "{starttime}" AND "{endtime}" AND kmtype="{type}"'
            cursor.execute(sql)
            rows = cursor.fetchall()
            total = 0
                
            for row in rows:
                if row['isk'] != None:
                    total = total + int(row["isk"])
            return(f'ISK {type.lower()} Total between {justdayleft} and {justdayright}: **Ƶ {total:,}**')

    def getbycorp(self,corp,type):
        cursor = self.db.cursor(dictionary=True)
        if type=="kill":
            sql = f'SELECT isk FROM killmail WHERE finalblow like "%[{corp}]%" and kmtype="{type}"'
        elif type=="loss":
            sql = f'SELECT isk FROM killmail WHERE name like "%[{corp}]%" and kmtype="{type}"'
        cursor.execute(sql)
        rows = cursor.fetchall()
        total = 0
        
        for row in rows:
            if row['isk'] != None:
                total = total + int(row["isk"])
        return(f'ISK {type} total for [{corp}] **Ƶ {total:,}**')
    def getbypilot(self,pilot,type):
        cursor = self.db.cursor(dictionary=True)
        if type=="kill":
            sql = f'SELECT isk FROM killmail WHERE finalblow like "%{pilot}%" and kmtype="{type}"'
        elif type=="loss":
            sql = f'SELECT isk FROM killmail WHERE name like "%{pilot}%" and kmtype="{type}"'
        cursor.execute(sql)
        rows = cursor.fetchall()
        total = 0
        
        for row in rows:
            if row['isk'] != None:
                total = total + int(row["isk"])
        return(f'ISK {type} total for {pilot}: **Ƶ {total:,}**')

#thing = KMDB()
#thing.checkduplicate({'message_id':"123435",'name': '[BFPC]Scar3crOw', 'isk': '296151618', 'time': '2021/02/15 23:22:09', 'playership': 'Slasher Interceptor Frigate', 'kmtype': 'KILL', 'playerid': '0', 'participants': '2', 'finalblow': '[DEAD]The Kiddo', 'location': 'K4-RFZ < 3B-IWE < Querious:'})
#print(thing.getbypilot("Caeser","kill"))