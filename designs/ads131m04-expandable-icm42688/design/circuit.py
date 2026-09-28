"""Revision B circuit specification. Pin numbers are physical package pads.
Generation is deterministic; engineering prototype, pending physical validation.
"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
parts=[]
def add(ref,value,fp,pins,xy,mpn='',section='Digital',rotation=0,names=None):
    parts.append(dict(ref=ref,value=value,footprint=fp,pins={str(k):v for k,v in pins.items()},x=xy[0],y=xy[1],rotation=rotation,mpn=mpn or value,section=section,names={str(k):v for k,v in (names or {}).items()}))
RFP='Resistor_SMD:R_0603_1608Metric'; CFP='Capacitor_SMD:C_0603_1608Metric'
def r(ref,value,a,b,x,y,section='Digital',rotation=0):
    add(ref,value,RFP,{1:a,2:b},(x,y),'RC0603FR-07'+{'100':'100RL','33':'33RL','1k':'1KL','3.3k':'3K3L','6.65k':'6K65L','10k':'10KL','100k':'100KL','1M':'1ML','316k':'316KL','5.1k':'5K1L'}[value],section,rotation)
def c(ref,value,a,b,x,y,section='Digital',rotation=0):
    mpns={'100nF':'GRM188R71C104KA01D','1uF':'GRM188R61A105KA61D','10nF':'GRM188R71H103KA01D','47nF':'GRM188R71H473KA61D','1nF':'GRM1885C1H102JA01D','220nF':'GRM188R71C224KA01D','2.2uF':'GRM188R60J225KE19D','22uF':'GRM21BR61A226ME44L','10uF':'GRM21BR61A106KE19L'}
    add(ref,value,CFP if value not in ['22uF','10uF'] else 'Capacitor_SMD:C_0805_2012Metric',{1:a,2:b},(x,y),mpns[value],section,rotation)
GH3='Connector_JST:JST_GH_BM03B-GHS-TBT_1x03-1MP_P1.25mm_Vertical'
GH8='Connector_JST:JST_GH_BM08B-GHS-TBT_1x08-1MP_P1.25mm_Vertical'
# Native module; GPIO35/36/37 reserved by octal PSRAM on N8R8.
gpios={4:'IMU_MOSI',5:'IMU_MISO',6:'IMU_SCK',7:'FOOT_CS',15:'SHANK_CS',16:'FOOT_INT',17:'SHANK_INT',18:'BUTTON',8:'ADC_DRDY',19:'USB_DM_MCU',20:'USB_DP_MCU',9:'ADC_RESET',10:'ADC_CS',11:'ADC_MOSI',12:'ADC_SCK',13:'ADC_MISO',21:'USB_PRESENT_N',47:'EXP_SDA',48:'EXP_SCL',0:'BOOT',38:'SD_CMD',39:'SD_CLK_MCU',40:'SD_D0',41:'LED_REC',42:'LED_ERR',44:'UART_RX',43:'UART_TX',2:'LED_LOW',1:'BAT_SENSE'}
padgpio={4:4,5:5,6:6,7:7,8:15,9:16,10:17,11:18,12:8,13:19,14:20,15:3,16:46,17:9,18:10,19:11,20:12,21:13,22:14,23:21,24:47,25:48,26:45,27:0,28:35,29:36,30:37,31:38,32:39,33:40,34:41,35:42,36:44,37:43,38:2,39:1}
p={1:'GND',2:'3V3D',3:'EN',40:'GND',41:'GND'};p.update({pad:gpios.get(gpio) for pad,gpio in padgpio.items()})
add('U1','ESP32-S3-WROOM-1-N8R8','RF_Module:ESP32-S3-WROOM-1',p,(12,13),names={**{pad:'GPIO'+str(gpio) for pad,gpio in padgpio.items()},1:'GND',2:'3V3',3:'EN',40:'GND',41:'EP_GND'})
c('C1','100nF','3V3D','GND',4,28);c('C2','10uF','3V3D','GND',7,28)
r('R1','10k','3V3D','EN',24,12);c('C3','1uF','EN','GND',24,15)
r('R2','10k','3V3D','BOOT',24,19);r('R3','10k','3V3D','BUTTON',24,23)
for ref,net,x,y in [('SW2','BOOT',25,28),('SW3','EN',25,33),('SW4','BUTTON',25,39)]:
    add(ref,net,'Button_Switch_SMD:SW_SPST_TL3342',{1:net,2:'GND'},(x,y),'TL3342F160QG')
# microSD native one-bit host. DAT1/2/3 retain pullups, detect contacts isolated.
add('J2','microSD','Connector_Card:microSD_HC_Hirose_DM3AT-SF-PEJM5',{1:'SD_D2',2:'SD_D3',3:'SD_CMD',4:'3V3D',5:'SD_CLK',6:'GND',7:'SD_D0',8:'SD_D1',9:None,10:None,'SH':'GND'},(37,40),'DM3AT-SF-PEJM5')
for i,net in enumerate(['SD_CMD','SD_D0','SD_D1','SD_D2','SD_D3']):r('R'+str(10+i),'10k','3V3D',net,31+i*2.7,29,rotation=90)
r('R15','33','SD_CLK_MCU','SD_CLK',24,25);c('C10','100nF','3V3D','GND',39,31);c('C11','22uF','3V3D','GND',43,31)
# Data-only USB. VBUS never connected to battery or regulated rails.
usb={x:'GND' for x in ['A1','A12','B1','B12','SH']};usb.update({x:'USB_VBUS' for x in ['A4','A9','B4','B9']});usb.update({'A5':'USB_CC1','B5':'USB_CC2','A6':'USB_DP','B6':'USB_DP','A7':'USB_DM','B7':'USB_DM','A8':None,'B8':None})
add('J1','USB-C (battery powered)','Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal',usb,(6,47),'USB4105-GF-A',rotation=0)
r('R20','5.1k','USB_CC1','GND',3,40);r('R21','5.1k','USB_CC2','GND',7,40)
r('R22','33','USB_DP','USB_DP_MCU',4,36);r('R23','33','USB_DM','USB_DM_MCU',4,38)
r('R24','100k','USB_VBUS','USB_GATE',10,40);r('R25','1M','USB_GATE','GND',13,40)
r('R26','10k','3V3D','USB_PRESENT_N',20,40)
add('Q2','2N7002','Package_TO_SOT_SMD:SOT-23',{1:'USB_GATE',2:'GND',3:'USB_PRESENT_N'},(19,42),'2N7002,215')
c('C12','10nF','USB_GATE','GND',13,42)
add('D1','USB ESD','Package_TO_SOT_SMD:SOT-23-6',{1:'USB_DP',2:'GND',3:'USB_DM',4:None,5:'USB_VBUS',6:None},(7,43),'USBLC6-2SC6')
# Locking IMU cable. Firmware starts shared SPI at 1 MHz; cable qualification pending.
for j,name,x in [('J3','FOOT',34),('J4','SHANK',48)]:
    add(j,name+' IMU',GH8,{1:'3V3D',2:'GND',3:'IMU_SCK',4:'IMU_MOSI',5:'IMU_MISO',6:name+'_CS',7:name+'_INT',8:'GND'},(x,5),'BM08B-GHS-TBT(LF)(SN)')
for i,(net,x) in enumerate([('FOOT_CS',28),('SHANK_CS',31)]):r('R'+str(30+i),'10k','3V3D',net,x,10)
# ADS131M04 TSSOP20 exact PW pin map.
add('U2','ADS131M04IPWR','Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm',{1:'3V0A',2:'GND',3:'AIN0P',4:'AIN0N',5:'AIN1N',6:'AIN1P',7:'AIN2P',8:'AIN2N',9:'AIN3N',10:'AIN3P',11:'ADC_RESET',12:'ADC_CS',13:'ADC_DRDY',14:'ADC_SCK',15:'ADC_MISO',16:'ADC_MOSI',17:'ADC_CLK',18:'ADC_CAP',19:'GND',20:'3V3D'},(47,21),section='ADC',names={1:'AVDD',2:'AGND',3:'AIN0P',4:'AIN0N',5:'AIN1N',6:'AIN1P',7:'AIN2P',8:'AIN2N',9:'AIN3N',10:'AIN3P',11:'SYNC_RESET_N',12:'CS_N',13:'DRDY_N',14:'SCLK',15:'DOUT',16:'DIN',17:'CLKIN',18:'CAP',19:'DGND',20:'DVDD'})
c('C20','1uF','3V0A','GND',41,18,'ADC');c('C21','1uF','3V3D','GND',53,18,'ADC');c('C22','220nF','ADC_CAP','GND',53,21,'ADC')
add('Y1','8.192 MHz','Oscillator:Oscillator_SMD_Abracon_ASE-4Pin_3.2x2.5mm',{1:'3V3D',2:'GND',3:'OSC_OUT',4:'3V3D'},(51,12),'ASE-8.192MHZ-LC-T','ADC')
r('R32','33','OSC_OUT','ADC_CLK',51,15,'ADC');c('C23','100nF','3V3D','GND',54,12,'ADC')
r('R33','10k','3V3D','ADC_CS',43,13,'ADC');r('R34','10k','3V3D','ADC_RESET',40,13,'ADC')
# Quiet 1.5 V midpoint. MCP6001 SOT23: 1OUT 2VSS 3IN+ 4IN- 5VDD.
r('R40','10k','3V0A','VMID_DIV',57,43,'Analog');r('R41','10k','VMID_DIV','GND',57,46,'Analog');c('C30','1uF','VMID_DIV','GND',60,46,'Analog')
add('U5','MCP6001T-I/OT','Package_TO_SOT_SMD:SOT-23-5',{1:'VMID_BUF',2:'GND',3:'VMID_DIV',4:'VMID_BUF',5:'3V0A'},(60,42),section='Analog')
r('R42','100','VMID_BUF','VMID',63,43,'Analog');c('C31','1uF','VMID','GND',66,43,'Analog');c('C32','100nF','3V0A','GND',60,39,'Analog')
# U3 = first unity buffers; U4 = attenuating second RC unity buffers.
quadpins=[(3,2,1),(5,6,7),(10,9,8),(12,13,14)]
for ref,stage,xy in [('U3','A',(60,16)),('U4','B',(60,32))]:
    pins={4:'3V0A',11:'GND'}
    for ch,(plus,minus,out) in enumerate(quadpins):pins.update({plus:f'RC{ch}{stage}',minus:f'BUF{ch}{stage}',out:f'BUF{ch}{stage}'})
    add(ref,'MCP6004T-I/ST','Package_SO:TSSOP-14_4.4x5mm_P0.65mm',pins,xy,section='Analog')
c('C33','100nF','3V0A','GND',55,16,'Analog');c('C34','100nF','3V0A','GND',55,32,'Analog')
for ch in range(4):
    y=8+ch*9
    add('J'+str(5+ch),'EMG'+str(ch+1),GH3,{1:'3V0A',2:'GND',3:f'RAW{ch}'},(71,y),'BM03B-GHS-TBT(LF)(SN)','Analog')
    n=100+ch*10
    r('R'+str(n),'3.3k',f'RAW{ch}',f'RC{ch}A',66,y+2,'Analog',90)
    r('R'+str(n+1),'1M',f'RAW{ch}','VMID',71,y+4,'Analog')
    c('C'+str(n),'47nF',f'RC{ch}A','GND',63,y+2,'Analog',90)
    # BAV199 dual series diodes pin1 anode lower, pin2 cathode upper, pin3 midpoint.
    add('D'+str(10+ch),'BAV199','Package_TO_SOT_SMD:SOT-23',{1:'GND',2:'3V0A',3:f'RC{ch}A'},(68,y+5),'BAV199,215','Analog')
    r('R'+str(n+2),'6.65k',f'BUF{ch}A',f'RC{ch}B',55,y+4,'Analog')
    r('R'+str(n+3),'6.65k','VMID',f'RC{ch}B',55,y+6,'Analog')
    c('C'+str(n+1),'47nF',f'RC{ch}B','GND',59,y+5,'Analog',90)
    r('R'+str(n+4),'100',f'BUF{ch}B',f'AIN{ch}P',40,y+8,'Analog')
    r('R'+str(n+5),'100','VMID',f'AIN{ch}N',40,y+10,'Analog')
    c('C'+str(n+2),'1nF',f'AIN{ch}P',f'AIN{ch}N',43,y+9,'Analog',90)
# Protected removable 1S battery required; no charger on board. Reverse battery PMOS.
add('J9','PROTECTED 1S BATTERY','Connector_JST:JST_GH_BM02B-GHS-TBT_1x02-1MP_P1.25mm_Vertical',{1:'PACK_PLUS',2:'GND'},(17,46),'BM02B-GHS-TBT(LF)(SN)','Power')
add('Q1','DMP2035U','Package_TO_SOT_SMD:SOT-23',{1:'GND',2:'VBAT',3:'PACK_PLUS'},(17,42),'DMP2035U-7','Power')
add('SW1','POWER','Button_Switch_SMD:SW_SPDT_CK_JS102011SAQN',{1:'VBAT',2:'POWER_EN',3:'GND'},(18,36),'JS102011SAQN','Power')
add('U6','TPS63070RNMR','RevB:TI_RNM0015A',{1:'GND',2:'POWER_GOOD',3:'VAUX',4:'GND',5:'FB',6:'GND',7:'3V3D',8:'3V3D',9:'SW_L2',10:'GND',11:'SW_L1',12:'VBAT',13:'VBAT',14:'POWER_EN',15:'GND'},(12,32),section='Power')
add('L1','1.5uH','Inductor_SMD:L_Coilcraft_XAL4020-XXX',{1:'SW_L1',2:'SW_L2'},(17,31),'XAL4020-152MEC','Power')
c('C40','22uF','VBAT','GND',9,30,'Power');c('C41','22uF','3V3D','GND',10,35,'Power');c('C42','22uF','3V3D','GND',13,36,'Power');c('C43','100nF','VAUX','GND',9,32,'Power')
r('R50','316k','3V3D','FB',9,34,'Power');r('R51','100k','FB','GND',9,36,'Power');r('R52','100k','3V3D','POWER_GOOD',17,28,'Power')
r('R53','100k','VBAT','BAT_SENSE',20,29,'Power');r('R54','100k','BAT_SENSE','GND',20,32,'Power');c('C44','100nF','BAT_SENSE','GND',20,34,'Power')
add('U7','TPS7A2030PDBVR','Package_TO_SOT_SMD:SOT-23-5',{1:'3V3D',2:'GND',3:'3V3D',4:None,5:'3V0A'},(49,44),section='Power')
c('C45','1uF','3V3D','GND',46,44,'Power');c('C46','1uF','3V0A','GND',52,44,'Power')
for i,(net,col,x) in enumerate([('LED_REC','green',30),('LED_ERR','red',35),('LED_LOW','amber',40)]):
    r('R'+str(60+i),'1k',net,net+'_A',x,10)
    add('D'+str(20+i),col,'LED_SMD:LED_0603_1608Metric',{1:'GND',2:net+'_A'},(x,13),['LTST-C190KGKT','LTST-C190KRKT','LTST-C190KSKT'][i])
add('J10','Expansion','Connector_JST:JST_GH_BM06B-GHS-TBT_1x06-1MP_P1.25mm_Vertical',{1:'3V3D',2:'GND',3:'EXP_SDA',4:'EXP_SCL',5:'UART_TX',6:'UART_RX'},(31,21),'BM06B-GHS-TBT(LF)(SN)')
for ref,x,y in [('H1',3,3),('H2',72,3),('H3',72,47)]:add(ref,'M2 mounting','MountingHole:MountingHole_2.2mm_M2',{},(x,y),'MECHANICAL','Mechanical')
main=list(parts)
placement=ROOT/'design'/'placement-main.json'
if placement.exists():
    locations=json.loads(placement.read_text())
    for p in main:
        if p['ref'] in locations:p['x'],p['y'],p['rotation']=locations[p['ref']]
if __name__=='__main__':
    (ROOT/'design'/'main.json').write_text(json.dumps({'board':'main','width_mm':75,'height_mm':50,'parts':main},indent=2)+'\n')
    (ROOT/'design'/'gpio-map.json').write_text(json.dumps(gpios,indent=2)+'\n')
