#!/usr/bin/env python3
"""Local synthetic AFW1 device emulator. Does NOT use an ESP32 or physical sensors."""
import argparse,json,socket,tempfile,time,sys
from pathlib import Path
from afo_format import read_header,decode_record
from generate_example import generate as generate_legacy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"simulations"))
from run_acquisition import generate
from live_protocol import encode_packet

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--port',type=int,default=3333);ap.add_argument('--seconds',type=float,default=10);ap.add_argument('--drop-every',type=int,default=0);ap.add_argument("--channels",type=int,choices=[2,4],default=2);ap.add_argument("--legacy",action="store_true");args=ap.parse_args()
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp)/'synthetic.afolog'
        if args.legacy:generate_legacy(path,args.seconds)
        else:generate(path,args.channels,duration=args.seconds)
        with path.open('rb') as f:meta=read_header(f);body=f.read()
    records=[body[i:i+64] for i in range(0,len(body),64)]
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
        sock.bind(('127.0.0.1',args.port));print('SYNTHETIC device waiting for laptop receiver on localhost',flush=True)
        hello,peer=sock.recvfrom(64)
        while hello!=b'AFO-LIVE1':hello,peer=sock.recvfrom(64)
        sock.setblocking(False);seq=0;start=time.monotonic();last_meta=-10
        def send(kind,payload,count=0):
            nonlocal seq
            seq+=1
            if kind==2 and args.drop_every and seq%args.drop_every==0:return
            sock.sendto(encode_packet(kind,0xDEADBEEF,1,seq,payload,count),peer)
        for i in range(0,len(records),16):
            batch=records[i:i+16];target=(decode_record(batch[-1]).timestamp_us-(1000000 if args.legacy else 0))/1e6
            delay=start+target-time.monotonic()
            if delay>0:time.sleep(delay)
            if time.monotonic()-last_meta>=.8:
                send(1,json.dumps(meta,separators=(',',':')).encode());last_meta=time.monotonic()
            send(2,b''.join(batch),len(batch))
            try:
                hello,source=sock.recvfrom(64)
                if hello==b'AFO-LIVE1':peer=source
            except BlockingIOError:pass
        print('Synthetic stream finished. Stop the receiver and inspect its files.',flush=True)
if __name__=='__main__':main()
