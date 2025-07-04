import pytest

import asm

# ======================================== _creTagDict
def test_creTagDict_smoke():

    res = asm._creTagDict(
        [
            { "cell_type": "code", "source": [ "a = 'hello asm'" ], "metadata": {"tags": [ "mac.hello" ] } },        
        ]
    )
    assert "hello" in res
    assert res["hello"] == "a = 'hello asm'"

def test_creTagDict_empty():

    res = asm._creTagDict([])

    assert res == {}

def test_creTagDict_only_code():

    res = asm._creTagDict(
        [
            { "cell_type": "markdown", "source": [ "will be skipped" ], "metadata": { "tags": [ "mac.0" ] } },        
            { "cell_type": "code", "source": [ "a = 'hello asm'" ], "metadata": { "tags": [ "mac.1" ] } },        
        ]
    )
    assert "1" in res
    assert res["1"] == "a = 'hello asm'"

def test_creTagDict_only_asm():

    res = asm._creTagDict(
        [
            { "cell_type": "code", "source": [ "a = 'hello asm'" ], "metadata": { "tags": [ "as" ] } },        
            { "cell_type": "code", "source": [ "a = 'hello asm'" ], "metadata": {"tags": [ "some_mac.1" ] } },        
            { "cell_type": "code", "source": [ "a = 'hello asm'" ], "metadata": {"tags": [ "as", "mac" ] } },        
            { "cell_type": "code", "source": [ "a = 'hello asm'" ], "metadata": {} },        
        ]
    )
    assert res == {}

def test_creTagDict_asm_with_smth():

    res = asm._creTagDict(
        [
            { "cell_type": "code", "source": [ "a = 'hello asm'" ], "metadata": { "tags": [ "mac." ] } },        
        ]
    )
    assert res == {}

def test_creTagDict_dupls():

    res = asm._creTagDict(
        [
            { "cell_type": "code", "source": [ "will be replaced" ], "metadata": { "tags": [ "mac.1" ] } },
            { "cell_type": "code", "source": [ "a = 'hello asm'" ], "metadata": { "tags": [ "mac.1" ] } },        
        ]
    )
    assert "1" in res
    assert res["1"] == "a = 'hello asm'"

# ======================================== _creMacList
def test_creMacList_smoke():

    res = asm._creMacList(
        [
            { "cell_type": "code", "source": [ "some macro def" ], "metadata": {"tags": [ "mdef" ] } },        
        ]
    )
    assert len(res)==1
    assert res[0] == "some macro def"

def test_creMacList_empty():

    res = asm._creMacList([])

    assert res == []

def test_creTagDict_only_code():

    res = asm._creMacList(
        [
            { "cell_type": "markdown", "source": [ "will be skipped" ], "metadata": { "tags": [ "mdef" ] } },        
            { "cell_type": "code", "source": [ "some macro def" ], "metadata": { "tags": [ "mdef" ] } },        
        ]
    )
    assert len(res)==1
    assert res[0] == "some macro def"

# ======================================================= _prepareSource
def test_prepareSource_smoke():

    ress,resn = asm._prepareSource(
        [
            { "cell_type": "markdown", "source": [ "#Header" ] },        
            { "cell_type": "code", "source": [ "hello asm" ], "metadata": { "tags": [ "mac.1" ] } },        
            { "cell_type": "code", "source": [ "  write {{ mac.1 }}" ], "metadata": { "tags": [ "mod" ] } },        
            { "cell_type": "code", "source": [ "  skip {{ mac.1 }}" ], "metadata": { "tags": [ "test" ] } },        
        ],
        "mod"
    )
    assert ress == [
        "  write {{ mac.1 }}"
    ]
    assert resn == []

def test_prepareSource_empty():

    ress, resn = asm._prepareSource([],"mod")
    assert ress == []
    assert resn == []

def test_prepareSource_no_source():

    ress, resn = asm._prepareSource(
        [
            { "cell_type": "markdown", "source": [ "#Header" ] },        
            { "cell_type": "code", "source": [ "hello asm" ], "metadata": { "tags": [ "mac.1" ] } },        
        ],
        "mod"
    )
    assert ress == []
    assert resn == []

def test_prepareSource_no_res_tag():

    ress, resn = asm._prepareSource(
        [
            { "cell_type": "markdown", "source": [ "#Header" ] },        
            { "cell_type": "code", "source": [ "hello asm" ], "metadata": { "tags": [ "mac.1" ] } },        
            { "cell_type": "code", "source": [ "  {{ mac.1 }}" ], "metadata": { "tags": [ "mod" ] } },        
        ],
        "test"
    )
    assert ress == []
    assert resn == []

def test_prepareSource_asm_and_what():

    ress, resn = asm._prepareSource(
        [
            { "cell_type": "markdown", "source": [ "#Header" ] },        
            { "cell_type": "code", "source": [ "hello asm" ], "metadata": { "tags": [ "mod","mac.1" ] } },        
            { "cell_type": "code", "source": [ "  write {{ mac.1 }}" ], "metadata": { "tags": [ "mod" ] } },        
            { "cell_type": "code", "source": [ "  skip {{ mac.1 }}" ], "metadata": { "tags": [ "test" ] } },        
        ],
        "mod"
    )
    assert ress == [
        "  write {{ mac.1 }}"
    ]
    assert resn == []

def test_prepareSource_what_and_not_what():

    ress, resn = asm._prepareSource(
        [
            { "cell_type": "code", "source": [ "  write1 {{ mac.1 }}" ], "metadata": { "tags": [ "test","mod" ] } },     
            { "cell_type": "code", "source": [ "  write2 {{ mac.1 }}" ], "metadata": { "tags": [ "mod","test" ] } },     
            { "cell_type": "code", "source": [ "  skip {{ mac.1 }}" ], "metadata": { "tags": [ "test" ] } },        
        ],
        "mod"
    )
    assert ress == [
        "  write1 {{ mac.1 }}",
        "  write2 {{ mac.1 }}",
    ]
    assert resn == []

# добавить тестов на пропуск JINJA

def test_prepareSource_no_jinja():

    ress, resn = asm._prepareSource(
        [
            { "cell_type": "code", "source": [ "hello asm" ], "metadata": { "tags": [ "mod","mac.1" ] } },        
            { "cell_type": "code", "source": [ "  write {{ mac.1 }}" ], "metadata": { "tags": [ "mod" ] } },        
            { "cell_type": "code", "source": [ "  nojinja {{ mac.1 }}" ], "metadata": { "tags": [ "mod", "nojinja" ] } },        
        ],
        "mod"
    )
    assert ress == [
        "  write {{ mac.1 }}",
        "  nojinja {{ mac.1 }}",
    ]
    assert resn == [1]

# можно еще напридумывать тестов здесь...

# ======================================================= _processList
@pytest.fixture
def stm():
    """ стандартный набор строк тестов подстановки """
    return {
        "v1": """a = 1
b = 2""",
        "v2": "print(123)",
    }
@pytest.fixture
def stmd():
    """ стандартный набор макроопределений """
    return [
        """{% macro aaa() %}
b = 12
b = 14
{% endmacro %}"""
    ]
    
def test_processList_smoke(stm,stmd):

    res = asm._processList(
        [
            "  {{ v1 }}",
            "  {{ aaa() }}",
            "  {{ v2 }}"
        ],
        [],
        stm,
        stmd
    )

    # здесь пустая строка появляется без пробелов... но она удаляется
    assert res == """  a = 1
  b = 2
  b = 12
  b = 14
  print(123)"""

def test_processList_preserve_spaces(stm,stmd):

    res = asm._processList(
        [
            " {{ v2 }}  {{ v2 }}   {{ v2 }}"
        ],
        [],
        stm,
        stmd
    )
        
    assert res == """ print(123)  print(123)   print(123)"""

def test_processList_preserve_space_mdef(stm,stmd):

    res = asm._processList(
        [
            "  {{ v1 }}",
            "  if b==0:",
            "      {{ aaa() }}",
            "  {{ v2 }}"
        ],
        [],
        stm,
        stmd
    )

    # здесь пустая строка появляется без пробелов...
    assert res == """  a = 1
  b = 2
  if b==0:
      b = 12
      b = 14
  print(123)"""

# ======================================================= processFile

# здесь пока "ломает" генерировать файл - используем руками созданные
# И ПРОВЕРЯЕМ ГЛАЗАМИ РЕЗУЛЬТИРУЮЩИЕ ФАЙЛЫ
# asm_smoke.ipynb: самый простой happy path
#   * содержит макрос
#   * содержит маркдаун ячейки (игнорируются)
#   * содержит кодовую ячейку типа mod (параметр по умолчанию)
#   * содержит кодовую ячейку типа test (попадает в тест)
#   * результат: файл asm_smoke.py, который глядим глазами
# asm_simple.ipynb: в нем более разнообразные случаи, простые для понимания
# asm_complex.ipynb: в нем уже затейливые случаи, в которые надо вникать, возможно - не реализованные

import os

def test_processFile_smoke():

    smokeFile = "asm_smoke.ipynb"
    resFile = "asm_smoke.py"
    
    if os.access(resFile,os.F_OK):
        os.remove(resFile)
        
    asm.processFile(smokeFile)
    
    assert os.access(resFile,os.F_OK)

def test_processFile_with_mod():

    smokeFile = "asm_smoke.ipynb"
    resFile = "asm_smoke.py"
    
    if os.access(resFile,os.F_OK):
        os.remove(resFile)
        
    asm.processFile(smokeFile,"mod")
    
    assert os.access(resFile,os.F_OK)

def test_processFile_with_test():

    smokeFile = "asm_smoke.ipynb"
    resFile = "test_asm_smoke.py"
    
    if os.access(resFile,os.F_OK):
        os.remove(resFile)
        
    asm.processFile(smokeFile,"test")
    
    assert os.access(resFile,os.F_OK)

def test_processFile_with_other():

    smokeFile = "asm_smoke.ipynb"
    resFiles = ["test_asm_smoke.py","asm_smoke.py"]

    for f in resFiles:
        if os.access(f,os.F_OK):
            os.remove(f)
        
    asm.processFile(smokeFile,"other")

    for f in resFiles:
        assert not os.access(f,os.F_OK)
