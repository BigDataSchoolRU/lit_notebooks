"""
Модуль для обработки низкоуровневых литературных ноутбуков (АССЕМБЛЕР)

Низкоуровневые ноутбуки позволяют

* воспользоваться ноутбуками для создания кода и тестов (т.о. иметь один файл с исходниками, тестами, документацией и "мусором")
* не использовать доп.разметку "литературного" стиля (заголовки функций, параметры и проч "вкусности")
* именно на этом уровне происходит "литературное" в смысле Кнутта программирование (=использование макросов и макровызовов)
    * на "литературном" уровне эти возможности "оборачиваются" во вкусности (т.е. ими становится проще пользоваться)

"""

""" TODO

* продумать и добавить тестов для ошибочных ситуаций
    * нет используемой макроподстановки - что скажет asm
    * нет используемого макроопределения - аналогично
    * вообще ошибочные ситуации - мы же используем jinja "под капотом"...

"""

"""
Как работает модуль:

* через processFile() получает ноутбук в формате Ассемблера (см. ниже)
* порождает на выходе питон файл (с тестами или кодом)

Формат входного файла

Входным файлом является IPYNB файл (JSON), обрабатываются только кодовые узлы:

* строится словарь строк "макропеременных"
    * среди тэгов должен быть тэги вида "mac.name"
* строится список строк "макроопределений"
    * среди тэгов должен быть тэги "mdef"
* все кодовые ячейки без таких тэгов (но с тэгом "типа" ячейки - mod или test) обрабатываются
    * jinja не используется, если есть тэг "nojinja", иначе
    * все вхождения "{{ name }}" заменяются на содержимое словаря (с сохранением выравнивания)
    * все вхождения "{{ name() }}" заменяются на вызов соответствуюего макро (с параметрами и сохранением выравнивания)

См. юнит-тесты и пример `asm_smoke.ipynb` в директории Examples.

"""

from typing import Dict, List, Tuple, Any

import json, os
import jinja2

def _creTagDict(srcList: List[Dict[str,Any]]) -> Dict[str,str]:
    """ Строит словарь макроподстановок 

    :param srcList: исходный ноутбук (его ячейки)
    :returns: словарь "код",строка

    Обрабатываем только ячейки, помеченные тэгом "mac.*".
    Дублирующие значения тупо перезаписывают предыдущий вариант (пока) 
    """

    resDict = {}
    for cell in srcList:
        if cell["cell_type"]!="code": # обрабатываем только кодовые ячейки
            continue
        if "tags" not in cell["metadata"]: # ячейки без тэгов пропускаем
            continue
        for tag in cell["metadata"]["tags"]:
            if tag.startswith("mac.") and len(tag)>4: # интересующий нас тэг присутствует
                macName = tag.split("mac.")[1].strip()
                resDict[macName] = "".join(cell["source"])
                break # дальше не ищем

    return resDict

def _creMacList(srcList: List[Dict[str,Any]]) -> List[str]:
    """ Строит список макроопределений 

    :param srcList: исходный ноутбук (его ячейки)
    :returns: список строк кода макроопределений (как есть)

    Обрабатываем только ячейки, помеченные тэгом "mdef".
    """

    resList = []
    for cell in srcList:
        if cell["cell_type"]!="code": # обрабатываем только кодовые ячейки
            continue
        if "tags" not in cell["metadata"]: # ячейки без тэгов пропускаем
            continue
        for tag in cell["metadata"]["tags"]:
            if tag=="mdef": # интересующий нас тэг присутствует
                resList += cell["source"]
                break # дальше не ищем

    return resList

def _prepareSource(srcList: List[Dict[str,Any]], what: str) -> Tuple[List[str],List[int]]:
    """ Готовит исходный файл для обработки - оставляет только обрабатываемые строки
    
    :param srcList: исходный ноутбук (его ячейки)
    :param what: тэг, участвующий в фильтрации ячеек с кодом
    :returns: 
        список обрабатываемых строк ноутбука
        список номеров строк, которые не надо пропускать через jinja
    """

    # собираем строки, которые потом надо обработать
    srcLines = []
    srcNumbs = []
    for cell in srcList:
        if cell["cell_type"]!="code": # обрабатываем только кодовые ячейки
            continue     
        if "tags" not in cell["metadata"]: # ячейки без тэгов пропускаем
            continue
        # macros должны всегда игнорироваться
        isMacro = False
        for tag in cell["metadata"]["tags"]:
            if tag=="mdef" or (tag.startswith("mac.") and len(tag)>4): # макросы
                isMacro = True
                break
        skipCell = True
        noJinja = False
        if not isMacro: # сюда попадаем только для кодовых ячеек без макросов
            for tag in cell["metadata"]["tags"]:
                if tag==what: # код нужного "типа"
                    skipCell = False
                if tag=="nojinja": # не нужно пропускать через jinja
                    noJinja = True
        if not skipCell:
            if noJinja: # нужно добавить номера добавляемых строк в список
                lastEl = len(srcLines) # пропускаем, начиная с этой строки
                lenCell = len(cell["source"]) # пропускаем столько строк
                srcNumbs += list(range(lastEl,lastEl+lenCell))
            srcLines += cell["source"]
    
    return (srcLines,srcNumbs)

def _processList(srcList: List[str], srcNumbs: List[int], macros: Dict[str,str], mdefs: List[str], rmEmptyLines: bool = True) -> str:
    """ JINJA: Заменяет вхождения макросов на их значения
    * макроподстановки дополняет indent()-ом
    * пропускает строки с номерами из srcNumbs

    :param srcList: исходный код (только обрабатываемые ячейки)
    :param srcNumbs: номера пропускаемых строк из предыдущего списка
    :param macros: словарь "код", строка
    :param mdefs: список макроопределений    
    :param rmEmptyLines: необходимость удаления пустых строк    
    :returns: строка с результатами макроподстановок в srcList

    """
    
    resList = []
    env = jinja2.Environment(trim_blocks=True)
    if mdefs:
        mStr = "\n".join(mdefs)+"\n" # макроопределения
    else:
        mStr = ""
    for i,ln in enumerate(srcList): # обрабатываем построчно
        if i in srcNumbs: # строку не нужно пропускать через Jinja
            resList.append(ln)
            continue
        mInd = ln.find("{{") 
        while mInd>=0: # выравниваем по началу макроса
            mEnd = ln.find("}}",mInd)
            ln = ln[:mEnd] + f"| indent({mInd}) }}}}" + ln[mEnd+2:]
            mInd = ln.find("{{",mInd+1)
        templ = env.from_string(mStr+ln)
        resList.append(templ.render(macros))

    retList = "\n".join(resList)
    if rmEmptyLines: # запишем только не пустые строки
        return "\n".join([ ln for ln in retList.split("\n") if len(ln.strip())>0 ])
    else:
        return retList

def processFile(notebook: str, what: str = "mod", rmEmptyLines: bool = True) -> None:
    """ Обрабатывает исходный файл (ноутбук)
    
    :param notebook: исходный ноутбук (имя файла)
    :param what: тэг, участвующий в фильтрации ячеек с кодом
    :param rmEmptyLines: необходимость удаления пустых строк    

    Побочный эффект функции - генерируемый файл
    * notebook.py: для what=="mod" (если в имени присутствует _asm, оно удаляется)
    * test_notebook.py: для what="test"
    * ничего не делает для всех остальных значений what

    При обработке в режиме создания тестового файла в файл добавляются
    стандартные строки
    * import <модуль>
    * import pytest
    """

    if what not in ["mod","test"]: # ничего не делаем
        return

    # разбираемся с именами файлов
    dirName,fileName = os.path.split(notebook)
    baseName = fileName.split(".ipynb")[0].replace("_asm","")
    resName = baseName if what=="mod" else "test_"+baseName
    resFile = os.path.join(dirName,resName+".py")

    with open(notebook,"r") as fp:
        js = json.load(fp)

    cells = js["cells"] # больше нам ничего не нужно - массив ячеек
    # print(cells)

    macros = _creTagDict(cells)             # собираем словарь макроподстановок
    mdefs = _creMacList(cells)              # собираем список макроопределений
    lines,numbs = _prepareSource(cells,what)  # оставляем только нужные строки
    if what=="test":                        # добавим стандартные строки
        lines = [ f"import {baseName}", "import pytest" ] + lines
    resStr = _processList(lines, numbs, macros, mdefs, rmEmptyLines) # заменяем макросы в них

    # сохраняем результат
    with open(resFile,"w") as fp:
        fp.write(resStr)
        