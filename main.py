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

from random import sample
from string import ascii_lowercase

class ObjListView(BoxLayout):
    def __init__(self, **kwargs):
        super(ObjListView, self).__init__(**kwargs)
        self.ids["header"].text = "Список объектов:"
        self.ids.rv_object.data = [{'name': objList[x].name,'upd_time':'время:' + objList[x].time_of_update.strftime("%d-%m-%Y %H:%M:%S") if objList[x].time_of_update is not None else "нет данных",'ob_color':{"red":(1.,0.,0.,1.),"green":(0.,1.,0.,1.),"yellow":(0.7,0.5,0.1,1.),"gray":(0.95,0.95,0.95,1.)}[objList[x].color]}  for x in range(len(objList))]
        Clock.schedule_once(self.update_gui, 1)
    def update_gui(self,dt):
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
            self.ob_color = {"red":(1.,0.,0.,1.),"green":(0.,1.,0.,1.),"yellow":(0.7,0.5,0.1,1.),"gray":(0.95,0.95,0.95,1.)}[self._ob.color]
            self.ids.rv_analog.data = [{'name': self._ob.get_adc_data(x)["name"],'value':'{0:0.02f}'.format(self._ob.get_adc_data(x)["value"]),'measure_unit':self._ob.get_adc_data(x)["measure_unit"]}
                            for x in range(self._ob.get_adc_number())]
            self.ids.rv_discrete.data = [{'name': self._ob.get_di_data(x)["name"],'value':str(self._ob.get_di_data(x)["value"])}
                            for x in range(self._ob.get_di_number())]
            self.ids.rv_message.data = [{'message': self._ob.get_msg_data(x)["message"],'type':self._ob.get_msg_data(x)["type"]}
                            for x in range(self._ob.get_msg_number())]
            Clock.schedule_once(self.update_gui, 1)
        
    def update_gui(self,dt):
        if self._ob is not None:
            self.ob_color = {"red":(1.,0.,0.,1.),"green":(0.,1.,0.,1.),"yellow":(0.7,0.5,0.1,1.),"gray":(0.95,0.95,0.95,1.)}[self._ob.color]
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
    def __init__(self, **kwargs):
        super(DispRoot, self).__init__(**kwargs)
        
        threading.Thread(target=self.subscribe_mqtt).start()
        
        self._view = "obj_list"
        self.add_widget(Factory.ObjListView())
    def show_current_object(self, name):       
        self._view = "object"
        obj_name = re.search(r'\[b\].+\[/b\]',name)
        obj_time = re.search(r'\[color=.+\] время:.+\[/color\]',name)
        

        self.clear_widgets()
        obj_name = "" if obj_name is None else obj_name.group(0)
        obj_name = re.sub(r'\[/?.\]','',obj_name).strip()

        current_obj = Factory.ObjView(obj_name)
        current_obj.obj_name = obj_name
        current_obj.obj_time = "нет данных" if obj_time is None else obj_time.group(0)
        current_obj.ids.list_button.text="Вернуться к списку объектов"
        self.add_widget(current_obj)
        
    def show_obj_list(self):
        self._view = "obj_list"
        self.clear_widgets()
        ob_list = ObjListView()
        self.add_widget(ob_list)
        
    def subscribe_mqtt(self):
        while True:
            if self.stop.is_set():
                return
            cnt = len(objList)
            if cnt:
                topic_list = [ob.topic for ob in objList if len(ob.topic)>=1]
                try:
                    msg = subscribe.simple(topic_list, hostname="m13.cloudmqtt.com",port=19363,auth= {'username':"kontel_plc", 'password':"plc"},client_id="".join(sample(ascii_lowercase, 15)))
                    ob = get_ob_by_topic(msg.topic)
                    if ob is not None:
                        ob.time_of_update = datetime.now()
                        for j in range(ob.get_adc_number()):
                            adc = ob.get_adc_data(j)
                            if type(msg.payload[0])!=int:
                                value = ord(msg.payload[13+j*2]) + ord(msg.payload[14+j*2])*256
                            else:
                                value = msg.payload[13+j*2] + msg.payload[14+j*2]*256
                            value *= adc["coeff"]
                            ob.update_adc_data(j,value)
                        ob.color = "green"
                    for i in range(len(objList)):
                        ob = objList[i]
                        if ob.mqtt_server is None:
                           ob.time_of_update = datetime.now()
                           ob.color = random.choice(("red","green","yellow","gray"))
                           for j in range(ob.get_adc_number()):
                               adc = ob.get_adc_data(j)
                               ob.update_adc_data(j,adc["value"]+1)
                           for j in range(ob.get_di_number()):
                               ob.update_di_data(j,random.randint(0,1))
                           msg_list = list([{"message":"".join(sample(ascii_lowercase, 15)),"type":{"red":[1.,0.,0.,1.],"green":[0.,1.,0.,1.],"yellow":[0.7,0.5,0.1,1.]}[random.choice(("red","green","yellow"))]} 
                           for x in range(random.randint(0,5))])  
                           ob.upd_msg_data(msg_list)
                           #objList[i] = ob  
                except Exception as ex:
                    pass
                    #print(ex)

class ObjState():
    def __init__(self, name):
        self._name = name
        self._time_of_update = None
        self._color = "gray"
        self._adc_data = []
        self._di_data = []
        self._msg_data = []
        self._topic = ""
        self._mqtt_server = None
        self._mqtt_port = 0
        self._mqtt_user_name = ""
        self._mqtt_password = ""
        
    @property
    def mqtt_user_name(self):
        return self._mqtt_user_name
    
    @mqtt_user_name.setter
    def mqtt_user_name(self,value):
        self._mqtt_user_name = value
        
    @property
    def mqtt_password(self):
        return self._mqtt_password
    
    @mqtt_password.setter
    def mqtt_password(self,value):
        self._mqtt_password = value
        
    @property
    def mqtt_port(self):
        return self._mqtt_port
    
    @mqtt_port.setter
    def mqtt_port(self,value):
        self._mqtt_port = value
        
    @property
    def mqtt_server(self):
        return self._mqtt_server
    
    @mqtt_server.setter
    def mqtt_server(self,value):
        self._mqtt_server = value
        
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
        
topicDict = {}
mqtt_clients = []
        
def readObjectsFromFile():
    ob_names = ("Владимир, Лермонтова 17", "Суздаль, Центральная 15", "Суздаль, Гороховая 3", "Ковров, Пушкина 56", "Юрьев-Польский, Солнечная 27")
    res_list = []
    
    ob = ObjState("Контэл - переговорная")
    ob.time_of_update = None#datetime.now()
    ob.add_adc_data({"name":"    Т помещения","value":0,"measure_unit":"град.","coeff":0.1})
    ob.topic = "4385017381/all"
    ob.mqtt_server = "m13.cloudmqtt.com" 
    ob.mqtt_port = 19363
    ob.mqtt_user_name = "kontel_plc"
    ob.mqtt_password = "plc"
    topicDict[ob.topic]=ob
    res_list.append(ob)
    
    for i in range(len(ob_names)):
        ob = ObjState(ob_names[i])
        ob.time_of_update = None
        for j in range(random.randint(1,10)):
            ob.add_adc_data({"name":"    adc"+str(j+1)+":","value":j,"measure_unit":"*","coeff":0.1})
            
        for j in range(random.randint(1,10)):
            ob.add_di_data({"name":"    di"+str(j+1)+":","value":random.randint(0,1)})
           
            
        msg_list = list([{"message":"".join(sample(ascii_lowercase, 15)),"type":{"red":[1.,0.,0.,1.],"green":[0.,1.,0.,1.],"yellow":[0.7,0.5,0.1,1.]}[random.choice(("red","green","yellow"))]} 
        for x in range(random.randint(0,5))])  
        ob.upd_msg_data(msg_list)
        topicDict[ob.topic] = ob
        res_list.append(ob)
    
    return sorted(res_list,key=lambda ob: ob.name)

objList =  readObjectsFromFile() 

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
    
class DispApp(App):
    
    def on_stop(self):
        self.root.stop.set()
    def build(self):
        return DispRoot()
    def on_pause(self):
        return True
    

if __name__=="__main__":
    app = DispApp()
    app.run()
