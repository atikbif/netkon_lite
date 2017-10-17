# File name: main.py
import kivy
kivy.require('1.10.0')


from kivy.app import App
from datetime import datetime
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
import random
import re
from kivy.factory import Factory
from kivy.uix.label import Label
import threading
import paho.mqtt.subscribe as subscribe
import paho.mqtt.client as mqtt

from random import sample
from string import ascii_lowercase

import xml.etree.ElementTree as ET
import sys

from kivy.utils import platform
from time import sleep

if platform!='win':
    from jnius import autoclass 
else:
    from kivy.core.audio import SoundLoader
    
from kivy.config import Config
Config.set('graphics', 'allow_screensaver', '0')



mqtt_server =""
mqtt_port = 0
mqtt_user = ""
mqtt_password = ""
objList =  [] 
topicDict = {}
mqtt_clients = []

PY2 = sys.version_info[0] == 2

def check_objects_update_time(dt):
    for ob in objList:
        ob_time = ob.time_of_update
        if ob_time:
            diff = (datetime.now() - ob_time).seconds
            if diff > 30*60:
                ob.color = "gray"
    Clock.schedule_once(check_objects_update_time, 60)

class ObjListView(BoxLayout):
    def __init__(self, **kwargs):
        super(ObjListView, self).__init__(**kwargs)
        self.ids["header"].text = "Список объектов:"
        self.ids.rv_object.data = [{'name': objList[x].name,'upd_time':'время:' + objList[x].time_of_update.strftime("%d-%m-%Y %H:%M:%S") if objList[x].time_of_update is not None else "нет данных",'ob_color':{"red":(1.,0.,0.,1.),"green":(0.,1.,0.,1.),"yellow":(0.7,0.5,0.1,1.),"gray":(0.95,0.95,0.95,1.)}[objList[x].color]}  for x in range(len(objList))]
        Clock.schedule_once(self.update_gui, 1)
    def update_gui(self,dt):
        self.ids.link_state.source = "link_on.png" if app.root.connect_state else "link_off.png"
        self.ids.rv_object.data = [{'name': objList[x].name,'upd_time':'время:' + objList[x].time_of_update.strftime("%d-%m-%Y %H:%M:%S") if objList[x].time_of_update is not None else "нет данных",'ob_color':{"red":(1.,0.,0.,1.),"green":(0.,1.,0.,1.),"yellow":(0.7,0.5,0.1,1.),"gray":(0.95,0.95,0.95,1.)}[objList[x].color]}  for x in range(len(objList))]
        Clock.schedule_once(self.update_gui, 1)    

class ObjView(BoxLayout):
    def __init__(self, obj_name, **kwargs):
        super(ObjView, self).__init__(**kwargs)
        self._name = obj_name
        self._ob = get_ob_by_name(obj_name)
        self.ids.adc.text = "аналоговые"
        self.ids.di.text = "дискретные"
        self.ids.msg.text = "сообщения"
        if self._ob is not None:
            self.ids.sound_check.active = self._ob.sound_on
            self.ob_color = {"red":(1.,0.,0.,1.),"green":(0.,1.,0.,1.),"yellow":(0.7,0.5,0.1,4.),"gray":(0.95,0.95,0.95,1.)}[self._ob.color]
            self.ids.rv_analog.data = [{'name': self._ob.get_adc_data(x)["name"],'value':'{0:0.02f}'.format(self._ob.get_adc_data(x)["value"]),'measure_unit':self._ob.get_adc_data(x)["measure_unit"]}
                            for x in range(self._ob.get_adc_number())]
            self.ids.rv_discrete.data = [{'name': self._ob.get_di_data(x)["name"],'value':str(self._ob.get_di_data(x)["value"])}
                            for x in range(self._ob.get_di_number())]
            self.ids.rv_message.data = [{'message': self._ob.get_msg_data(x)["message"],'type':self._ob.get_msg_data(x)["type"]}
                            for x in range(self._ob.get_msg_number())]
            Clock.schedule_once(self.update_gui, 1)
        
    def update_gui(self,dt):
        if self._ob is not None:
            self.ob_color = {"red":(1.,0.,0.,1.),"green":(0.,1.,0.,1.),"yellow":(0.7,0.5,0.1,4.),"gray":(0.95,0.95,0.95,1.)}[self._ob.color]
            self.obj_time = r"[color=C0C0C0]время:" + self._ob.time_of_update.strftime("%d-%m-%Y %H:%M:%S") if self._ob.time_of_update is not None else "нет данных" + r"[/color]"
            self.ids.rv_analog.data = [{'name': self._ob.get_adc_data(x)["name"],'value':'{0:0.02f}'.format(self._ob.get_adc_data(x)["value"]),'measure_unit':self._ob.get_adc_data(x)["measure_unit"]}
                        for x in range(self._ob.get_adc_number())]
            self.ids.rv_discrete.data = [{'name': self._ob.get_di_data(x)["name"],'value':str(self._ob.get_di_data(x)["value"])}
                        for x in range(self._ob.get_di_number())]
            self.ids.rv_message.data = [{'message': self._ob.get_msg_data(x)["message"],'type':self._ob.get_msg_data(x)["type"]}
                        for x in range(self._ob.get_msg_number())]
            Clock.schedule_once(self.update_gui, 1)


class DispRoot(BoxLayout):
    stop = threading.Event()
    connect_state = False
    if platform=='win': sound = SoundLoader.load('alarm.wav')
    def __init__(self, **kwargs):
        super(DispRoot, self).__init__(**kwargs)
        
        self._thread = threading.Thread(target=self.subscribe_mqtt)
        self._thread.daemon=True
        self._thread.start()
        
        self._view = "obj_list"
        self.add_widget(Factory.ObjListView())
        self.current_obj = None
            
        
    def show_current_object(self, name): 
        obj_name = re.search(r'\[b\].+\[/b\]',name)
        obj_time = re.search(r'\[color=.+\] время:.+\[/color\]',name)
        

        self.clear_widgets()
        obj_name = "" if obj_name is None else obj_name.group(0)
        obj_name = re.sub(r'\[/?.\]','',obj_name).strip()

        self.current_obj = Factory.ObjView(obj_name)
        self.current_obj.obj_name = obj_name
        self.current_obj.obj_time = "нет данных" if obj_time is None else obj_time.group(0)
        self.current_obj.ids.list_button.text="Вернуться к списку объектов"
        self.add_widget(self.current_obj)
        
    def show_obj_list(self):
        self.current_obj = None
        self.clear_widgets()
        ob_list = ObjListView()
        self.add_widget(ob_list)
        
    def activate_sound(self,checkbox, value):
        if self.current_obj is not None:
            
            ob = get_ob_by_name(self.current_obj.obj_name)
            if ob: 
                ob.sound_on = value
                #print(value)
        
    def update_ob_data(self,ob,mqtt_data):
        ob.time_of_update = datetime.now()
        for j in range(ob.get_adc_number()):
            adc = ob.get_adc_data(j)
            if PY2:
                value = ord(mqtt_data[12+j*2])*256 + ord(mqtt_data[13+j*2])
            else:
                value = mqtt_data[12+j*2]*256 + mqtt_data[13+j*2]
            value *= adc["coeff"]
            ob.update_adc_data(j,value)
        for j in range(ob.get_di_number()):
            byte_num = 4 + (j//8)
            bit_num = j%8
            if PY2:
                value = ord(mqtt_data[byte_num]) & (1 << bit_num)
            else:
                value = mqtt_data[byte_num] & (1 << bit_num)
            ob.update_di_data(j,value)
        color = "green"
        msg_list = []
        for j in range(ob.get_msg_conf_number()):
            byte_num = 72 + 4 + (j//8)
            bit_num = j%8
            if PY2:
                value = ord(mqtt_data[byte_num]) & (1 << bit_num)
            else:
                value = mqtt_data[byte_num] & (1 << bit_num)
            if value:
                msg = ob.get_msg_conf(j)
                if len(msg):
                    msg_list.append({"message":msg["name"],"type":{"red":[1.,0.,0.,1.],"green":[0.,1.,0.,1.],"yellow":[0.7,0.5,0.1,4.]}[msg["type"]]})
                    if msg["type"]=="red": 
                        if ob.color != "red":
                            if ob.sound_on:
                                if platform=='win': self.__class__.sound.play()
                                else:
                                    MediaPlayer = autoclass('android.media.MediaPlayer')

                                    mPlayer = MediaPlayer()
                                    mPlayer.setDataSource('alarm.wav')
                                    mPlayer.prepare()
                                    mPlayer.start()
                                    sleep(3)
                                    mPlayer.release()
                                    
                                    PythonActivity = autoclass('org.kivy.android.PythonActivity')
                                    Context = autoclass('android.content.Context')
                                    activity = PythonActivity.mActivity
                                    vibrator = activity.getSystemService(Context.VIBRATOR_SERVICE)
                                    if vibrator.hasVibrator(): vibrator.vibrate(1000)
                        color="red"
                    if msg["type"]=="yellow" and color!="red": color="yellow"
        ob.upd_msg_data(msg_list) 
        ob.color = color 

    def _on_connect(self,client, userdata, flags, rc):
        if rc != 0: 
            self.__class__.connect_state = False
            #print("NOT_CONNECT",str(rc))
        else: 
            self.__class__.connect_state = True
            #print("on_connect")
        topic_list = [(ob.topic,2) for ob in objList if len(ob.topic)>=1]
        client.subscribe(topic_list)
        pass
        
    def _on_message(self,client,userdata, msg):
        ob = get_ob_by_topic(msg.topic)
        if ob is not None:
            self.update_ob_data(ob,msg.payload)
    
    def _on_disconnect(self,client, userdata, rc):
        self.__class__.connect_state = False
        #print("ON_DISCONNECT")
        
    
    def subscribe_mqtt(self):
        while True:
            if self.stop.is_set():
                return
            cnt = len(objList)
            if cnt:
                while True:
                    try:
                        client = mqtt.Client(client_id="netkon"+"".join(sample(ascii_lowercase, 15)))
                        client.connect(mqtt_server, port=mqtt_port)
                        client.username_pw_set(mqtt_user, mqtt_password)
                        client.on_message = self._on_message
                        client.on_connect = self._on_connect
                        client.on_disconnect = self._on_disconnect
                        client.loop_forever()
                        break
                    except Exception as ex:
                        sleep(3)
                        #print(str(ex))
                
                # topic_list = [ob.topic for ob in objList if len(ob.topic)>=1]
                # try:
                    # msg = subscribe.simple(topic_list, hostname=mqtt_server,port=mqtt_port,auth= {'username':mqtt_user, 'password':mqtt_password},client_id="netkon"+"".join(sample(ascii_lowercase, 15)))
                    # ob = get_ob_by_topic(msg.topic)
                    # if ob is not None:
                        # self.update_ob_data(ob,msg.payload)
                # except Exception as ex:
                    # pass

class ObjState():
    def __init__(self, name):
        self._name = name
        self._time_of_update = None
        self._color = "gray"
        self._adc_data = []
        self._di_data = []
        self._msg_data = []
        self._msg_conf =[]
        self._topic = ""
        self._sound_on = True
        
    @property
    def sound_on(self):
        return self._sound_on
    
    @sound_on.setter
    def sound_on(self,value):
        self._sound_on = value
      
    @property
    def topic(self):
        return self._topic
    
    @topic.setter
    def topic(self,value):
        self._topic = value
        
    @property
    def color(self):
        return self._color

    @color.setter
    def color(self,value):
        val_list = ("gray","red","yellow","green")
        if value in val_list:
            self._color = value
        else:
            raise ValueError("value({0}) has to be in list:{1}".format(value,val_list))
            
    @property
    def time_of_update(self):
        return self._time_of_update
        
    @time_of_update.setter
    def time_of_update(self,value):
        if value==None or isinstance(value,datetime):
            self._time_of_update = value
        else:
            raise TypeError("The type of value({}) has to be Datetime")

    @property
    def name(self):
        return self._name
        
    def add_adc_data(self,value):
        self._adc_data.append(value)
        
    def get_adc_number(self):
        return len(self._adc_data)
        
    def get_adc_data(self,num):
        return None if num >= len(self._adc_data) else self._adc_data[num]
        
    def update_adc_data(self,num,value):
        if num < len(self._adc_data):
            self._adc_data[num]["value"]=value
            
    def add_di_data(self,value):
        self._di_data.append(value)
        
    def get_di_number(self):
        return len(self._di_data)
        
    def get_di_data(self,num):
        return None if num >= len(self._di_data) else self._di_data[num]
        
    def update_di_data(self,num,value):
        if num < len(self._di_data):
            self._di_data[num]["value"]=value
            
    def get_msg_number(self):
        return len(self._msg_data)
        
    def get_msg_data(self,num):
        return None if num >= len(self._msg_data) else self._msg_data[num]
        
    def upd_msg_data(self,messages):
        self._msg_data = messages
        
    def set_msg_conf(self,msg_conf):
        self._msg_conf = msg_conf
        
    def get_msg_conf(self,num):
        if num<len(self._msg_conf):
            return {"name":self._msg_conf[num]["name"],"type":self._msg_conf[num]["type"]}
        else:
            return {}
    def get_msg_conf_number(self):
        return len(self._msg_conf)
        
def readObjectsFromFile():
    global mqtt_server
    global mqtt_port
    global mqtt_user
    global mqtt_password
    
    res_list = []
    
    try:
        tree = ET.parse(App.get_running_app().user_data_dir + '/conf.xml')
    except:
        try:
            tree = ET.parse('/sdcard/Download/conf.xml')
        except:
            tree = ET.parse('default.xml')
    try:
        root = tree.getroot()
        
        for xml_mqtt in root.findall('mqtt'):
            mqtt_server = xml_mqtt.attrib["server"].encode('utf-8') if PY2 else xml_mqtt.attrib["server"]
            mqtt_port = int(xml_mqtt.attrib["port"].encode('utf-8')) if PY2 else int(xml_mqtt.attrib["port"])
            mqtt_user = xml_mqtt.attrib["user"].encode('utf-8') if PY2 else xml_mqtt.attrib["user"]
            mqtt_password = xml_mqtt.attrib["password"].encode('utf-8') if PY2 else xml_mqtt.attrib["password"]
            break

        for xml_ob in root.findall('object'):
            ob = ObjState(xml_ob.attrib["name"].encode('utf-8')) if PY2 else ObjState(xml_ob.attrib["name"])
            ob.time_of_update = None
            ob.topic = xml_ob.attrib["topic"].encode('utf-8') if PY2 else xml_ob.attrib["topic"]
            if len(ob.topic): topicDict[ob.topic] = ob
            for adc in xml_ob.findall('adc'):
                name = adc.attrib["name"].encode('utf-8') if PY2 else adc.attrib["name"]
                meas = adc.attrib["measure_unit"].encode('utf-8') if PY2 else adc.attrib["measure_unit"]
                coeff = adc.attrib["coeff"].encode('utf-8') if PY2 else adc.attrib["coeff"]
                ob.add_adc_data({"name":"    "+name+":","value":0,"measure_unit":meas,"coeff":float(coeff)})
            for di in xml_ob.findall('di'):
                name = di.attrib["name"].encode('utf-8') if PY2 else di.attrib["name"]
                ob.add_di_data({"name":"    "+name+":","value":0})
            msg_conf = []
            for msg in xml_ob.findall('msg'):
                name = msg.attrib["name"].encode('utf-8') if PY2 else msg.attrib["name"]
                type = msg.attrib["type"].encode('utf-8') if PY2 else msg.attrib["type"]
                msg_conf.append({"name":name,"type":type})
            ob.set_msg_conf(msg_conf)
            res_list.append(ob)
            
    except Exception as ex:
        ob = ObjState(str(ex))
        res_list.append(ob)
   
    return sorted(res_list,key=lambda ob: ob.name)   

def get_ob_by_name(obj_name) :
    for i in range(len(objList)):
        if objList[i].name == obj_name:
            return objList[i]
    return None

def get_ob_by_topic(topic):
    for i in range(len(objList)):
        if objList[i].topic == topic:
            return objList[i]
    return None
    
class NetkonApp(App):
    
    def on_stop(self):
        self.root.stop.set()
    def build(self):
        global objList
        objList =  readObjectsFromFile()
        check_objects_update_time(None)
        return DispRoot()
    def on_pause(self):
        return True
    

if __name__=="__main__":
    app = NetkonApp()
    app.run()
