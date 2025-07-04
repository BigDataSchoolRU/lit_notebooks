def _getFuncName(cellContent):
    # разбирает содержимое
    funcName = cellContent[0].split("## ")[1] # предполагаем, что может быть заголовком уровня 2 и выше
    funcName = funcName.split("::")[0] # возможен комментарий, его убираем
    return funcName.strip() # убираем пробелы, если есть
def procFuncTag(cellContent, tag, func, **kwargs):
    # результат
    match tag:
        case "function":
            return ( "mod", [f"""def {_getFuncName(cellContent)}("""] )
        case "class":
            return ( "mod", [f"""class {_getFuncName(cellContent)}:"""] )
        case "method":
            return ( "mod", [f"""    def {_getFuncName(cellContent)}(self,"""] )
        case "testdef":
            return ( "test", [f"""def test_{func}_{_getFuncName(cellContent)}("""] )
def procParamTag(cellContent, tag, **kwargs):
    # numInst -> int = 4:: сколько штук нужно сгенерировать
    # разбирает содержимое
    parStr = cellContent[0].split("::")[0] # возможен комментарий, его убираем
    # результат
    return ( "test" if tag=="testparam" else "mod", [f"""    {parStr},"""] )
def procReturnTag(cellContent, tag, isMethod, **kwargs):
    # int:: вычисленный факториал числа
    # разбирает содержимое
    retStr = cellContent[0].split("::")[0].strip() # возможен комментарий, его убираем
    if len(retStr)>0:
        retStr = f" -> {retStr}"
    # результат
    indent = ""
    if isMethod:
        indent = "    "
    return ( "mod", [f"""{indent}){retStr}:"""] )
def procBodyTag(cellContent, tag, **kwargs):
    lines = []
    indent = "    "
    # добавляем завершение заголовка функции
    if not kwargs["wasReturn"]:
        valStr = "):\n"
        if tag=="methodbody":
            valStr = indent + valStr
        lines.append(valStr)
    # разбираем содержимое
    if tag in ["block","testblock"]: # не добавляем выравнивание
        indent = ""
    if tag=="methodbody": # удваиваем выравнивание
        indent = indent + indent
    for ln in cellContent:
        lines.append(indent+ln) # копируем строки, добавляя выравнивание если нужно
    # результат
    return ( "test" if tag in ["testbody","testblock"] else "mod", lines )
tag2Func = {
    "function": procFuncTag,
    "param": procParamTag,
    "testparam": procParamTag,    
    "return": procReturnTag,
    "body": procBodyTag,
    "testbody": procBodyTag,
    "testdef": procFuncTag,
    "block": procBodyTag,
    "testblock": procBodyTag,
    "class": procFuncTag,
    "method": procFuncTag,
    "methodbody": procBodyTag,
}
import json, os
def genAsmNotebook(litNb):
    with open(litNb,"r") as fp:
        js = json.load(fp)
    cells = js["cells"] # больше нам ничего не нужно - массив ячеек
    asmCells = []
    curFuncName = ""
    wasReturn = True # с таким значением не будет происходить генерации лишнего для блоков кода (типа import)        
    isMethod = False
    for cell in cells:
        if "tags" not in cell["metadata"]: # ячейки без тэгов пропускаем
            continue
        for tag in cell["metadata"]["tags"]: # пока нет смысла давать ячейкам более одного тэга (видимо), но все же цикл...
            if tag=="function" or tag=="method": # запомним в контексте имя функции
                curFuncName = _getFuncName(cell["source"])
                if tag=="function": # обрабатываем не метод
                    isMethod = False
                else:
                    isMethod = True
            if tag in ["function","method","testdef"]: # сбросим информацию о наличии тэга return
                wasReturn = False    
            if tag=="return": # запомним в контексте наличие return
                wasReturn = True
            if tag in ["test","mod","mdef"] or tag.find("mac.")==0: # пробрасываем ячейку как есть в asm ноутбук
                asmCells.append(cell)
            if tag in tag2Func.keys():
                cellTag,cellCode = tag2Func[tag](cell["source"],tag,func=curFuncName,wasReturn=wasReturn,isMethod=isMethod)
                newCell = {
                   "cell_type": "code",
                   # "execution_count": null,
                   "metadata": {
                        "editable": True,
                        "tags": [ cellTag ],
                   },
                   "outputs": [],
                   "source": cellCode
                }
                asmCells.append(newCell)
                if tag in ["body","testbody","methodbody"]: # обработали тело, надо сбросить необходимость добаления ):
                    wasReturn = True
    # сохраняем результат
    dirName,fileName = os.path.split(litNb)
    baseName = fileName.split(".ipynb")[0]
    resName = baseName+"_asm"
    resFile = os.path.join(dirName,resName+".ipynb")
    js["cells"] = asmCells
    with open(resFile,"w") as fp:
        json.dump(js,fp)
    return resFile
def genFuncSpec(litNb,fName,addTask=True):
    with open(litNb,"r") as fp:
        js = json.load(fp)
    cells = js["cells"] # больше нам ничего не нужно - массив ячеек
    lnList = []
    parList = []
    retList = []
    testList = []
    docStr = ""
    toBreak = False
    for cell in cells:
        if toBreak:
            break
        if "tags" not in cell["metadata"]: # ячейки без тэгов пропускаем
            continue
        for tag in cell["metadata"]["tags"]: # пока нет смысла давать ячейкам более одного тэга (видимо), но все же цикл...
            if tag in ["function","class"]:
                if _getFuncName(cell["source"])==fName: # наша функция
                    lnList.append(f"функция {fName}:\n")
                    continue
                else: # другая
                    if lnList: # нашу функцию уже обработали
                        toBreak = True
            if lnList: # обрабатываем описание нашей функции
                if tag=="doc":
                    lnList += ["".join(cell["source"])]
                if tag=="param":
                    if not parList:
                        parList.append(["Функция имеет следующие параметры:"])
                    parList.append([ "* " + ln for ln in cell["source"]])
                if tag=="return":
                    if not retList:
                        retList.append(["Результатами функции должно быть:"])
                    retList.append([ "* " + ln for ln in cell["source"]])
                if tag=="testbody":
                    if not testList:
                        testList.append(["Примеры использования (юнит-тесты - должны выполняться успешно):"])
                    testList.append(cell["source"]) # список - тест может быть большим
                    testList.append([""]) # разделитель
    resStr = "\n".join(lnList)
    if parList:
        resStr += "\n\n" + "\n".join(["\n".join(pEl) for pEl in parList])
    if retList:
        resStr += "\n\n" + "\n".join(["\n".join(rEl) for rEl in retList])
    if testList:
        resStr += "\n\n" + "\n\n".join(["".join(tEl) for tEl in testList])
    if addTask:
        resStr += "\nмне нужен код функции на python"
    return resStr