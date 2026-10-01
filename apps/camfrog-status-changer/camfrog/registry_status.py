from __future__ import annotations
import os, re, string
from dataclasses import dataclass

SENSITIVE=("password","token","session","cookie","credential","auth","secret")
@dataclass(frozen=True)
class HistoryValue:
    text: str
    source: str
    value_name: str

def _valid(s:str)->bool:
    s=s.strip().replace("\x00","")
    if not s or s.isdigit() or "@" in s or len(s)>160: return False
    if re.fullmatch(r"[0-9A-Fa-f]{24,}",s): return False
    if any(ord(c)<32 and c not in "\t" for c in s): return False
    printable=sum(c in string.printable or ord(c)>127 for c in s)
    return printable/max(1,len(s))>.9

def _extract(value):
    if isinstance(value,list): return [str(x) for x in value]
    if isinstance(value,str): return re.split(r"[\r\n|;]+",value)
    if isinstance(value,(bytes,bytearray)):
        out=[]
        b=bytes(value)
        for enc in ("utf-16le","utf-8","latin1"):
            try: out += re.split(r"[\r\n|;\x00]+",b.decode(enc,errors="ignore"))
            except Exception: pass
        return out
    return []

def read_camfrog_custom_statuses():
    if os.name!="nt": return []
    import winreg
    found=[]; seen=set()
    roots=[
        r"Software\Camfrog",
    ]
    views=[winreg.KEY_WOW64_64KEY,winreg.KEY_WOW64_32KEY]
    def walk(hive,path,view):
        try: key=winreg.OpenKey(hive,path,0,winreg.KEY_READ|view)
        except OSError: return
        try:
            i=0
            while True:
                try: name,val,_typ=winreg.EnumValue(key,i); i+=1
                except OSError: break
                low=(path+"\"+name).casefold()
                if any(x in low for x in SENSITIVE): continue
                if "status" not in low and "custom" not in low: continue
                for raw in _extract(val):
                    text=str(raw).strip()
                    if _valid(text) and text.casefold() not in seen:
                        seen.add(text.casefold()); found.append(HistoryValue(text,path,name))
            j=0
            while True:
                try: child=winreg.EnumKey(key,j); j+=1
                except OSError: break
                walk(hive,path+"\"+child,view)
        finally: winreg.CloseKey(key)
    for view in views:
        for root in roots: walk(winreg.HKEY_CURRENT_USER,root,view)
    return found

def merge_presets(existing, history):
    out=[]; seen=set()
    for x in list(existing)+[h.text if hasattr(h,"text") else str(h) for h in history]:
        v=str(x).strip()
        if v and v.casefold() not in seen:
            seen.add(v.casefold()); out.append(v)
    return out
