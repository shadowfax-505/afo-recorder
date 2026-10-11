"""AFW1 UDP telemetry framing. Independent packet CRC plus unchanged AFR1 record CRCs."""
import json,struct,zlib
from afo_format import decode_record,FormatError,RECORD_SIZE
PREFIX=struct.Struct('<4sBBHIIIIHH')
# Must equal WIFI_LIVE_METADATA_MAX in firmware/main/board.h. Older firmware sent at most 1280.
# MPU-6050 metadata exceeds one 1,500-byte MTU; the metadata datagram is IP-fragmented.
MAX_PAYLOAD=1800

def encode_packet(kind,boot,session,sequence,payload,count=0,dropped=0):
    if len(payload)>MAX_PAYLOAD:raise FormatError('oversize live packet')
    prefix=PREFIX.pack(b'AFW1',1,kind,count,boot,session,sequence,dropped,len(payload),0)
    return prefix+struct.pack('<I',zlib.crc32(prefix+payload))+payload

def decode_packet(data):
    if len(data)<32:raise FormatError('short live packet')
    magic,version,kind,count,boot,session,sequence,dropped,length,reserved=PREFIX.unpack_from(data)
    if magic!=b'AFW1' or version!=1 or reserved or length>MAX_PAYLOAD or len(data)!=32+length:
        raise FormatError('invalid live framing/version/length')
    if zlib.crc32(data[:28]+data[32:])!=struct.unpack_from('<I',data,28)[0]:raise FormatError('live packet CRC mismatch')
    payload=data[32:];result=dict(kind=kind,boot=boot,session=session,sequence=sequence,dropped=dropped,payload=payload)
    if kind==1:
        if count:raise FormatError('metadata count must be zero')
        try:meta=json.loads(payload)
        except (ValueError,UnicodeDecodeError) as exc:raise FormatError('invalid live metadata') from exc
        if not isinstance(meta,dict):raise FormatError('metadata must be an object')
        result['metadata']=meta
    elif kind==2:
        if not 1<=count<=16 or length!=count*RECORD_SIZE:raise FormatError('invalid live record count')
        result['records']=[decode_record(payload[i:i+64]) for i in range(0,length,64)]
    else:raise FormatError('unsupported live packet kind')
    return result
