from  kivy.app import App
from datetime import datetime
from kivy.uix.boxlayout import BoxLayout
from kivy.adapters.listadapter import ListAdapter
from kivy.uix.listview import ListItemButton, ListView
from kivy.clock import Clock
from kivy.adapters.models import SelectableDataItem
import random
from kivy.uix.listview import ListItemButton
import re
from kivy.factory import Factory
from kivy.uix.label import Label
from kivy.core.window import Window


class AnalogDataView(BoxLayout):
    pass

class AnalogData(BoxLayout):
    def __init__(self, obj_name,**kwargs):
        super(AnalogData, self).__init__(**kwargs)
        self._adc = []
        self._name = obj_name
        
        self._ob = get_ob_by_name(obj_name)
        if self._ob is not None:
            adc_number = self._ob.get_adc_number()
        
            self.add_widget(Label(text="Аналоговые данные:"))
            for i in range(adc_number):
                adc_ob = self._ob.get_adc_data(i)
                adc_widget = Factory.AnalogDataView()
                adc_widget.ids["name"].text = adc_ob["name"]
                adc_widget.ids["value"].text = str(adc_ob["value"])
                adc_widget.ids["measure_unit"].text = adc_ob["measure_unit"]
                self._adc.append(adc_widget)
                self.add_widget(adc_widget)
            Clock.schedule_interval(self.update_data, 10)
    def update_data(self,dt):
            for i in range(len(self._adc)):
                adc_widget = self._adc[i]
                adc_ob = self._ob.get_adc_data(i)
                adc_widget.ids["name"].text = adc_ob["name"]
                adc_widget.ids["value"].text = str(adc_ob["value"])
                adc_widget.ids["measure_unit"].text = adc_ob["measure_unit"]

class ObjView(BoxLayout):
    def __init__(self, obj_name, **kwargs):
        super(ObjView, self).__init__(**kwargs)
        self._name = obj_name
        self._ob = get_ob_by_name(obj_name)
        self.add_widget(AnalogData(obj_name))
        Clock.schedule_interval(self.update_test, 10)
        
    def update_test(self,dt):
        if self._ob is not None:
            self.obj_time = self._ob.time_of_update.strftime("%d-%m-%Y %H:%M:%S")


class DispRoot(BoxLayout):
    def __init__(self, **kwargs):
        super(DispRoot, self).__init__(**kwargs)
        Window.bind(on_keyboard=self.key_input)
        self._view = "obj_list"
        self.add_widget(ObjListView())
    def show_current_object(self, name):
        self._view = "object"
        obj_name = re.search(r'\[b\].+\[/b\]',name)
        obj_time = re.search(r'\[color=C0C0C0\] время:.+\[/color\]',name)
        

        self.clear_widgets()
        obj_name = "" if obj_name is None else obj_name.group(0)
        current_obj = Factory.ObjView(obj_name)
        current_obj.obj_name = obj_name
        current_obj.obj_time = "Нет данных" if obj_time is None else obj_time.group(0)
        current_obj.ids.list_button.text="Список объектов"
        self.add_widget(current_obj)
        
    def show_obj_list(self):
        self._view = "obj_list"
        self.clear_widgets()
        ob_list = ObjListView()
        self.add_widget(ob_list)
        
    def key_input(self, window, key, scancode, codepoint, modifier):
        if key == 27:
            if self._view=="object":
                self.show_obj_list()
            else:
                app.stop()
            return True # override the default behaviour
        else: # the key now does nothing
            return False

class LocationButton(ListItemButton):
    pass

class ObjState(SelectableDataItem):
    def __init__(self, name, **kwargs):
        super(ObjState, self).__init__(**kwargs)
        self._name = name
        self._time_of_update = None
        self._color = "gray"
        self._adc_data = []
        
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
        if isinstance(value,datetime):
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
        
def readObjectsFromFile():
    ob_names = ("Владимир, Почаевская 10","Владимир, Лермонтова 17", "Владимир, Мира 8", "Суздаль, Центральная 15", "Суздаль, Гороховая 3", "Ковров, Пушкина 56", "Юрьев-Польский, Солнечная 27")
    res_list = []
    for i in range(len(ob_names)):
        ob = ObjState(ob_names[i])
        ob.time_of_update = datetime.now()
        for j in range(i+1):
            ob.add_adc_data({"name":"adc"+str(j+1),"value":j,"measure_unit":"*"*(j+1)})
        res_list.append(ob)
    
    return sorted(res_list,key=lambda ob: ob.name)

objList =  readObjectsFromFile() 

def get_ob_by_name(obj_name) :
    obj_name = re.sub(r'\[/?.\]','',obj_name)
    
    for i in range(len(objList)):
        if objList[i].name == obj_name:
            return objList[i]
    return None
    
def update_ob_data(dt):
    for i in range(len(objList)):
        ob = objList[i]
        ob.time_of_update = datetime.now()
        ob.color = random.choice(("red","green","yellow","gray"))
        for j in range(ob.get_adc_number()):
            adc = ob.get_adc_data(j)
            ob.update_adc_data(j,adc["value"]+1)
        objList[i] = ob    
    
update_ob_data(None)
Clock.schedule_interval(update_ob_data, 30)

class ObjListView(BoxLayout):
    def __init__(self, **kwargs):
        super(ObjListView, self).__init__(**kwargs)
        list_item_args_converter = lambda row_index, obj: {'markup': True,
                                                           'text': "[b]" + obj.name + "[/b]" if obj.time_of_update is None else "[b]" + obj.name + "[/b]" + "[color=C0C0C0] время:" + obj.time_of_update.strftime("%d-%m-%Y %H:%M:%S")+"[/color]",
                                                           'size_hint_y': None,
                                                           'height': '100dp',
                                                           'deselected_color':{"red":[1.,0.,0.,1.],"green":[0.,1.,0.,1.],"yellow":[0.7,0.5,0.1,1.],"gray":[0.95,0.95,0.95,1.]}[obj.color],
                                                           'halign':'left',
                                                           'text_size':(self.width*0.9,None)}

        self.list_adapter = \
                ListAdapter(data=objList,
                            args_converter=list_item_args_converter,
                            selection_mode='single',
                            propagate_selection_to_data=False,
                            cls=LocationButton)

        self.list_view = ListView(adapter=self.list_adapter)

        self.add_widget(self.list_view)
        Clock.schedule_interval(self.update_ob_gui, 10)
        
    def update_ob_gui(self,dt):
        adaptObjList = self.list_adapter.data
        
        for i in range(len(adaptObjList)):
            adaptObjList[i] = objList[i]
            

class DispApp(App):
    def build(self):
        return DispRoot()

    

if __name__=="__main__":
    app = DispApp()
    app.run()
