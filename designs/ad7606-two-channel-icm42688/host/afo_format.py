"""AFO v1 binary format. All container integers are little endian.

IMU FIFO bytes retain the sensor's big-endian byte order. No interpolation,
normalization, or filtering is applied when decoding.
"""
from __future__ import annotations
from dataclasses import dataclass
import json
import struct
import zlib

HEADER_SIZE = 4096
RECORD_SIZE = 64
HEADER = struct.Struct('<8sHHI')
RECORD = struct.Struct('<4sBBHIQ40sI')
EMG = struct.Struct('<HHIIII')
EMG_B = struct.Struct('<4iHHIIB3xQ')
IMU = struct.Struct('<16sQQQ')
FIFO = struct.Struct('>B6hbH')
STATUS = struct.Struct('<10I')
KINDS = {1: 'emg', 2: 'foot', 3: 'shank', 4: 'status', 5: 'end', 6:'emg',7:'emg'}
LENGTHS = {1: EMG.size, 2: IMU.size, 3: IMU.size, 4: STATUS.size, 5: STATUS.size, 6:EMG_B.size,7:EMG_B.size}
STATUS_NAMES = ('timer_missed', 'queue_dropped', 'imu_errors', 'fifo_overflows',
                'adc_errors', 'emg_records', 'foot_records', 'shank_records',
                'battery_mv', 'queue_high_water')

class FormatError(ValueError):
    pass

def make_header(metadata: dict) -> bytes:
    encoded = json.dumps(metadata, separators=(',', ':'), allow_nan=False).encode()
    if len(encoded) > HEADER_SIZE - 20:
        raise FormatError('metadata too large')
    body = (HEADER.pack(b'AFOLOG1\0', 1, HEADER_SIZE, len(encoded)) + encoded).ljust(HEADER_SIZE-4, b'\0')
    return body + struct.pack('<I', zlib.crc32(body))

def read_header(stream) -> dict:
    data = stream.read(HEADER_SIZE)
    if len(data) != HEADER_SIZE:
        raise FormatError('incomplete file header; cannot infer configuration')
    magic, version, size, length = HEADER.unpack_from(data)
    if magic != b'AFOLOG1\0' or version != 1 or size != HEADER_SIZE:
        raise FormatError('unsupported file signature or version')
    if length > HEADER_SIZE - 20 or zlib.crc32(data[:-4]) != struct.unpack_from('<I', data, HEADER_SIZE-4)[0]:
        raise FormatError('header checksum/length failure; cannot safely recover configuration')
    try:
        meta = json.loads(data[16:16+length])
    except (ValueError, UnicodeDecodeError) as exc:
        raise FormatError('invalid metadata JSON') from exc
    if not isinstance(meta, dict) or meta.get('schema') not in ('afo-recorder/1','afo-recorder/2','afo-recorder/3'):
        raise FormatError('unsupported metadata schema')
    for name in ('emg_hz', 'imu_hz', 'adc_reference_mv', 'accel_range_g', 'gyro_range_dps'):
        value = meta.get(name)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 < value < 1000000:
            raise FormatError(f'invalid metadata field: {name}')
    if meta.get('adc_bits') != ({'afo-recorder/1':12,'afo-recorder/2':24,'afo-recorder/3':16}[meta['schema']]) or meta.get('record_bytes') != 64:
        raise FormatError('unsupported ADC resolution or record size')
    if meta['schema'] in ('afo-recorder/2','afo-recorder/3'):
        count=meta.get('active_channel_count');names=meta.get('emg_channels')
        if count not in (2,4) or isinstance(count,bool) or not isinstance(names,list) or len(names)!=count or any(not isinstance(n,str) or not n for n in names) or len(set(names))!=count:
            raise FormatError('invalid active channel count or identities')
        if meta['schema']=='afo-recorder/2':
            if meta.get('input_scale')!=.5 or meta.get('adc_pga')!=1 or meta.get('adc_osr')!=512:
                raise FormatError('unsupported Rev B scaling or ADC filter configuration')
            midpoint=meta.get('input_midpoint_mv')
            if not isinstance(midpoint,(int,float)) or isinstance(midpoint,bool) or not 0<midpoint<3000:
                raise FormatError('invalid input midpoint')
            if meta.get('adc_clock_hz')!=8192000 or meta['emg_hz']!=8000:
                raise FormatError('unsupported Rev B sample clock')
        else:
            expected={'adc_model':'AD7606','adc_reference_mv':5000,'input_scale':1,'input_midpoint_mv':0,'adc_osr':1,'adc_sensor_crc_supported':False,'emg_hz':8000}
            if any(meta.get(k)!=v for k,v in expected.items()):raise FormatError('unsupported AD7606 configuration')
    return meta

def make_record(kind: int, sequence: int, timestamp_us: int, payload: bytes, flags: int=0) -> bytes:
    if kind not in LENGTHS or len(payload) != LENGTHS[kind]:
        raise FormatError('incorrect payload size/type')
    body = RECORD.pack(b'AFR1', kind, flags, len(payload), sequence, timestamp_us,
                       payload.ljust(40, b'\0'), 0)[:-4]
    return body + struct.pack('<I', zlib.crc32(body))

@dataclass(frozen=True)
class Record:
    kind: int
    flags: int
    sequence: int
    timestamp_us: int
    payload: bytes
    offset: int

def decode_record(data: bytes, offset: int=0) -> Record:
    if len(data) != RECORD_SIZE:
        raise FormatError(f'truncated record at byte {offset}')
    magic, kind, flags, length, seq, timestamp, payload, crc = RECORD.unpack(data)
    if magic != b'AFR1' or zlib.crc32(data[:-4]) != crc:
        raise FormatError(f'record signature/checksum failure at byte {offset}')
    if kind not in LENGTHS or length != LENGTHS[kind]:
        raise FormatError(f'unsupported record type/length at byte {offset}')
    return Record(kind, flags, seq, timestamp, payload[:length], offset)

def iter_records(stream, recover: bool=False, issues: list | None=None):
    """Strict by default. Recovery scans for CRC-validated records without guessing data."""
    issues = issues if issues is not None else []
    bad_start = None
    while True:
        offset = stream.tell()
        data = stream.read(RECORD_SIZE)
        if not data:
            if bad_start is not None:
                issues.append({'kind': 'corrupt_bytes', 'start': bad_start, 'end': offset})
            return
        try:
            record = decode_record(data, offset)
        except FormatError:
            if not recover:
                raise
            if bad_start is None:
                bad_start = offset
            if len(data) < RECORD_SIZE:
                issues.append({'kind': 'corrupt_or_truncated_tail', 'start': bad_start, 'end': offset+len(data)})
                return
            stream.seek(offset+1)
            continue
        if bad_start is not None:
            issues.append({'kind': 'corrupt_bytes', 'start': bad_start, 'end': offset})
            bad_start = None
        yield record

def decode_fifo(data: bytes) -> dict:
    header, ax, ay, az, gx, gy, gz, temperature, timestamp = FIFO.unpack(data)
    if header & 0xfc != 0x68:
        raise FormatError(f'unsupported IMU FIFO header 0x{header:02x}')
    return dict(header=header, ax=ax, ay=ay, az=az, gx=gx, gy=gy, gz=gz,
                temperature_raw=temperature, sensor_timestamp_raw=timestamp,
                valid=all(x != -32768 for x in (ax, ay, az, gx, gy, gz)))

def status_values(payload: bytes) -> dict:
    return dict(zip(STATUS_NAMES, STATUS.unpack(payload)))

def decode_emg_b(record,metadata):
    if (metadata.get('schema'),record.kind) not in [('afo-recorder/2',6),('afo-recorder/3',7)]:raise FormatError('ADC frame type disagrees with session')
    values=EMG_B.unpack(record.payload)
    codes=values[:4];status,crc,duration,slots,mask,start=values[4:]
    count=metadata['active_channel_count']
    if mask!=(1<<count)-1:raise FormatError('frame channel mask disagrees with metadata')
    if any(codes[count:]):raise FormatError('disabled channel contains nonzero data')
    limit=1<<(metadata['adc_bits']-1)
    if any(x < -limit or x >= limit for x in codes[:count]):raise FormatError('ADC code outside signed range')
    if record.kind==7 and (status or crc):raise FormatError('AD7606 has no status/CRC word')
    if slots<1:raise FormatError('EMG elapsed_slots must be positive')
    return codes[:count],status,crc,duration,slots,start
