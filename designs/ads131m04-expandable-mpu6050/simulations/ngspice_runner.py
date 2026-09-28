"""Small synchronous adapter for the ngspice shared library; no external service."""
import ctypes as C
import ctypes.util
import os
from pathlib import Path
import numpy as np

class Complex(C.Structure):
    _fields_=[('real',C.c_double),('imag',C.c_double)]
class Vector(C.Structure):
    _fields_=[('name',C.c_char_p),('type',C.c_int),('flags',C.c_short),
              ('real',C.POINTER(C.c_double)),('complex',C.POINTER(Complex)),('length',C.c_int)]

class Spice:
    def __init__(self):
        candidates=[os.environ.get('NGSPICE_LIBRARY'),ctypes.util.find_library('ngspice'),
            '/Applications/KiCad/KiCad.app/Contents/Frameworks/libngspice.0.dylib',
            '/Applications/KiCad/KiCad.app/Contents/PlugIns/sim/libngspice.0.dylib']
        self.lib=None
        for name in filter(None,candidates):
            try:self.lib=C.CDLL(name);self.path=name;break
            except OSError:pass
        if self.lib is None:raise RuntimeError('Set NGSPICE_LIBRARY to your ngspice shared library path.')
        self.messages=[]
        callback=C.CFUNCTYPE(C.c_int,C.c_char_p,C.c_int,C.c_void_p)
        self.callback=callback(lambda text,i,p:self._log(text))
        self.lib.ngSpice_Init.argtypes=[C.c_void_p]*7
        self.lib.ngSpice_Init(self.callback,None,None,None,None,None,None)
        self.lib.ngSpice_Circ.argtypes=[C.POINTER(C.c_char_p)]
        self.lib.ngSpice_Command.argtypes=[C.c_char_p]
        self.lib.ngGet_Vec_Info.argtypes=[C.c_char_p]
        self.lib.ngGet_Vec_Info.restype=C.POINTER(Vector)
    def _log(self,text):self.messages.append(text.decode(errors='replace'));return 0
    def command(self,command):
        if self.lib.ngSpice_Command(command.encode())!=0:raise RuntimeError(command+' failed')
    def circuit(self,text):
        self.command('destroy all')
        lines=[line.encode() for line in text.splitlines()]+[None]
        if self.lib.ngSpice_Circ((C.c_char_p*len(lines))(*lines))!=0:
            raise RuntimeError('SPICE circuit load failed')
    def vector(self,name):
        ptr=self.lib.ngGet_Vec_Info(name.encode())
        if not ptr:raise RuntimeError('SPICE vector unavailable: '+name+'\n'+'\n'.join(self.messages[-12:]))
        v=ptr.contents
        if v.length<=0:raise RuntimeError('Empty SPICE result')
        if bool(v.complex):return np.array([v.complex[i].real+1j*v.complex[i].imag for i in range(v.length)])
        return np.ctypeslib.as_array(v.real,shape=(v.length,)).copy()
