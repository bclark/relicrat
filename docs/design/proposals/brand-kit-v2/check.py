"""Check import palette contrast and SVG asset well-formedness."""
import json, math
from pathlib import Path
from xml.etree import ElementTree as ET
root=Path(__file__).parent

def luminance(color):
 c=[int(color[i:i+2],16)/255 for i in (1,3,5)]
 return sum((v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4)*w for v,w in zip(c,(.2126,.7152,.0722)))
def contrast(a,b):
 x,y=sorted([luminance(a),luminance(b)])
 return (y+.05)/(x+.05)
for file in root.glob('*-PROPOSED.json'):
 theme=json.loads(file.read_text());c=theme['colors'];ratios=[contrast(c[f],c[b]) for f in ['ink','muted','accent'] for b in ['page','paper','soft']]+[contrast(c['accent_text'],c['accent'])]
 assert min(ratios)>=4.5,(file,min(ratios))
 assert set(c)=={'page','paper','ink','muted','rule','accent','accent_text','soft'}
 print(file.name, 'minimum text contrast',round(min(ratios),2))
for file in (root/'assets').glob('*.svg'):
 ET.parse(file)
 print(file.name,'valid XML')
