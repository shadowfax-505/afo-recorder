#!/usr/bin/env python3
"""Receive ESP32 unicast UDP, archive original records, serve a local live display."""
from __future__ import annotations
import argparse,collections,io,json,socket,struct,threading,time,uuid,webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from afo_format import decode_mpu,decode_emg_b,EMG,IMU,FIFO,STATUS,STATUS_NAMES,make_header,read_header,FormatError
from live_protocol import decode_packet

class Capture:
    def __init__(self,out):
        self.out=Path(out);self.out.mkdir(parents=True,exist_ok=False)
        self.raw=(self.out/'arrival_packets.afowifi').open('xb');self.raw.write(b'AFOWIFI1')
        self.lock=threading.Lock();self.sessions={};self.current=None;self.last_packet={};self.latest=None
        self.stats=dict(packets=0,packet_gaps=0,reordered_or_duplicate=0,invalid_packets=0,unknown_session_packets=0,device_queue_drops=0)
        self.last_rx=0;self.last_data=0;self.error=None
    def accept(self,data,now=None):
        now=time.monotonic() if now is None else now
        with self.lock:
            self.raw.write(struct.pack('<QI',time.time_ns(),len(data))+data)
            try:p=decode_packet(data)
            except FormatError:self.stats['invalid_packets']+=1;return
            self.stats['packets']+=1;self.last_rx=now
            boot=p['boot'];seq=p['sequence'];last=self.last_packet.get(boot)
            if last is not None:
                delta=(seq-last)&0xffffffff
                if delta==0 or delta>=0x80000000:self.stats['reordered_or_duplicate']+=1;return
                self.stats['packet_gaps']+=delta-1
            self.last_packet[boot]=seq;self.stats['device_queue_drops']=p['dropped']
            key=f'{boot:08x}-{p["session"]:08x}'
            if p['kind']==1:
                if p['session']==0:return
                if key not in self.sessions:
                    meta=dict(p['metadata']);meta.update(transport='wifi_udp',live_capture=True)
                    try:header=make_header(meta);read_header(io.BytesIO(header))
                    except (FormatError,ValueError,TypeError):self.stats['invalid_packets']+=1;return
                    f=(self.out/(key+'.afolog')).open('xb');f.write(header)
                    self.sessions[key]=dict(file=f,metadata=meta,emg=collections.deque(maxlen=1600),imu={},health={},
                        first_time=None,records=0,ended=False,first_sequence={},sequence_gaps={},last_sequence={})
                self.current=key;return
            if key not in self.sessions:self.stats['unknown_session_packets']+=1;return
            s=self.sessions[key];self.current=key;self.last_data=now
            for i,r in enumerate(p['records']):
                # Preserve original record bytes and device timestamps, without interpolation.
                s['file'].write(p['payload'][64*i:64*(i+1)]);s['records']+=1
                if r.kind in (1,2,3,6,7,8,9):
                    prev=s['last_sequence'].get(r.kind)
                    s['first_sequence'].setdefault(r.kind,r.sequence)
                    if prev is not None:
                        delta=(r.sequence-prev)&0xffffffff
                        if delta>1:s['sequence_gaps'][r.kind]=s['sequence_gaps'].get(r.kind,0)+delta-1
                    s['last_sequence'][r.kind]=r.sequence
                if r.kind in (6,7):
                    try:values,*_=decode_emg_b(r,s['metadata'])
                    except FormatError:
                        self.stats['invalid_packets']+=1;continue
                    scale=s['metadata']['adc_reference_mv']/(1<<(s['metadata']['adc_bits']-1))/1000
                    s['emg'].append((r.timestamp_us/1e6,*[v*scale for v in values],r.sequence,r.flags))
                elif r.kind==1:
                    a,b,*_=EMG.unpack(r.payload)
                    if s['first_time'] is None:s['first_time']=r.timestamp_us
                    scale=s['metadata']['adc_reference_mv']/4096/1000
                    s['emg'].append((r.timestamp_us/1e6,a*scale,b*scale,r.sequence,r.flags))
                elif r.kind in (2,3,8,9):
                    fifo,*_=IMU.unpack(r.payload)
                    try:
                        if r.kind in (8,9):
                            d=decode_mpu(fifo,s['metadata']);axes=[d[k] for k in ('ax','ay','az','gx','gy','gz')];gyro_scale=1/16.4
                        else:
                            if s['metadata'].get('imu_model')=='MPU6050':raise FormatError('ICM record in MPU session')
                            axes=FIFO.unpack(fifo)[1:7];gyro_scale=s['metadata']['gyro_range_dps']/32768
                    except FormatError:
                        self.stats['invalid_packets']+=1;continue
                    s['imu']['foot' if r.kind in (2,8) else 'shank']={'accel_g':[n*s['metadata']['accel_range_g']/32768 for n in axes[:3]],
                        'gyro_dps':[n*gyro_scale for n in axes[3:]],'sequence':r.sequence,'timestamp_us':r.timestamp_us,'flags':r.flags,
                        'timing_method':'irq estimate' if r.kind in (8,9) else 'sensor timestamp + IRQ'}
                elif r.kind in (4,5):
                    s['health']=dict(zip(STATUS_NAMES,STATUS.unpack(r.payload)))
                    if r.kind==5:s['ended']=True;s['stop_reason']=r.flags;s['file'].flush()
            self.raw.flush()
    def snapshot(self):
        with self.lock:
            now=time.monotonic();s=self.sessions.get(self.current)
            result={'stats':dict(self.stats),'error':self.error,'session':self.current,'packet_age_s':now-self.last_rx if self.last_rx else None,
                    'data_age_s':now-self.last_data if self.last_data else None,'output':str(self.out),'emg':[],'imu':{},'health':{}}
            if s:
                result.update(metadata=s['metadata'],emg=list(s['emg'])[-800:],imu=dict(s['imu']),health=dict(s['health']),records=s['records'],
                    ended=s['ended'],first_sequence=dict(s['first_sequence']),sequence_gaps=dict(s['sequence_gaps']),stop_reason=s.get('stop_reason'))
            return result
    def close(self):
        with self.lock:
            for s in self.sessions.values():s['file'].close()
            self.raw.close()
            summary={'transport':'wifi_udp','not_a_replacement_for_sd':True,'statistics':self.stats,
                     'sessions':{k:{'records':s['records'],'ended':s['ended'],'first_sequence':s['first_sequence'],'sequence_gaps':s['sequence_gaps']} for k,s in self.sessions.items()}}
            (self.out/'wireless_quality.json').write_text(json.dumps(summary,indent=2)+'\n')

def receive(capture,device,port,stop):
    try:
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,2*1024*1024)
            sock.bind(('',0));sock.connect((device,port));sock.settimeout(.2);hello=0
            while not stop.is_set():
                now=time.monotonic()
                if now-hello>=1:
                    try:sock.send(b'AFO-LIVE1')
                    except OSError:pass
                    hello=now
                try:data=sock.recv(2048)
                except (socket.timeout,ConnectionRefusedError):continue
                try:capture.accept(data)
                except OSError as exc:
                    with capture.lock:capture.error='Laptop capture stopped: '+str(exc)
                    return
    except OSError as exc:
        with capture.lock:capture.error='Wi-Fi receiver error: '+str(exc)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--device',default='192.168.4.1');ap.add_argument('--udp-port',type=int,default=3333)
    ap.add_argument('--http-port',type=int,default=8766);ap.add_argument('--out',type=Path);ap.add_argument('--no-browser',action='store_true');ap.add_argument('--duration',type=float)
    args=ap.parse_args();out=args.out or Path('live_captures')/(datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6])
    capture=Capture(out);stop=threading.Event();worker=threading.Thread(target=receive,args=(capture,args.device,args.udp_port,stop),daemon=True)
    html=(Path(__file__).with_name('live_view.html')).read_bytes()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path=='/':body=html;mime='text/html; charset=utf-8'
            elif self.path=='/api':body=json.dumps(capture.snapshot(),allow_nan=False).encode();mime='application/json'
            else:self.send_error(404);return
            self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers()
            try:self.wfile.write(body)
            except (BrokenPipeError,ConnectionResetError):pass
        def log_message(self,*args):pass
    try:server=ThreadingHTTPServer(('127.0.0.1',args.http_port),Handler)
    except OSError:
        capture.close();raise
    worker.start();url=f'http://127.0.0.1:{server.server_port}/'
    print(f'Live viewer: {url}\nConnect laptop Wi-Fi to AFO-Recorder-B. Captures: {out}\nCtrl+C stops reception and finalizes the laptop files.',flush=True)
    if not args.no_browser:webbrowser.open(url)
    if args.duration:threading.Timer(args.duration,server.shutdown).start()
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:stop.set();worker.join(2);server.server_close();capture.close()
if __name__=='__main__':main()
