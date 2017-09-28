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


class ObjView(BoxLayout):
    def __init__(self, obj_name, **kwargs):
        super(ObjView, self).__init__(**kwargs)
        self._name = obj_name
        Clock.schedule_interval(self.update_test, 10)
        
    def update_test(self,dt):
        new_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        self.obj_time = new_time


class DispRoot(BoxLayout):
    def __init__(self, **kwargs):
        super(DispRoot, self).__init__(**kwargs)
        self.add_widget(ObjListView())
    def show_current_object(self, name):
        obj_name = re.search(r'\[b\].+\[/b\]',name)
        obj_time = re.search(r'\[color=C0C0C0\] время:.+\[/color\]',name)
        

        self.clear_widgets()
        current_obj = Factory.ObjView(obj_name)
        current_obj.obj_name = "" if obj_name is None else obj_name.group(0)
        current_obj.obj_time = "Нет данных" if obj_time is None else obj_time.group(0)
        current_obj.ids.list_button.text="Список объектов"
        self.add_widget(current_obj)
        
    def show_obj_list(self):
        self.clear_widgets()
        ob_list = ObjListView()
        self.add_widget(ob_list)

class LocationButton(ListItemButton):
    pass

class ObjState(SelectableDataItem):
    def __init__(self, name, **kwargs):
        super(ObjState, self).__init__(**kwargs)
        self._name = name
        self._time_of_update = None
        self._color = "gray"
        
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
        
def readObjectsFromFile():
    ob_names = ("Владимир, Почаевская 10","Владимир, Лермонтова 17", "Владимир, Мира 8", "Суздаль, Центральная 15", "Суздаль, Гороховая 3", "Ковров, Пушкина 56", "Юрьев-Польский, Солнечная 27")
    res_list = []
    for i in range(len(ob_names)):
        ob = ObjState(ob_names[i])
        ob.time_of_update = datetime.now()
        res_list.append(ob)
    
    return sorted(res_list,key=lambda ob: ob.name)

objList =  readObjectsFromFile()  
    
def update_ob_data(dt):
    for i in range(len(objList)):
        ob = objList[i]
        ob.time_of_update = datetime.now()
        ob.color = random.choice(("red","green","yellow","gray"))
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
