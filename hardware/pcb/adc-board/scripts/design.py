"""Single source of truth for the open-fp ADC board: parts, nets, BOM data.

Both gen_sch.py (system Python) and gen_pcb.py (KiCad's bundled Python 3.9)
import this, so keep it plain Python 3.9 with no dependencies.

Firmware pin map (fixed, see docs/wiring.md):
  CS L1 D3, L2 D4, L3 D5, L4 D6, R1 D7, R2 D8, R3 D9, R4 A2
  SCLK D13, MOSI D11, MISO D12, L1 DRDY D2. Never D0, D1, D10.
"""
import uuid

PROJECT = 'adc-board'
NS = uuid.UUID('6f1c2a3e-0b7d-4e51-9a3c-0f9e1d2c3b4a')


def uid(*parts):
    return str(uuid.uuid5(NS, '/'.join(str(p) for p in parts)))


ROOT_UUID = uid('root-sheet')

# channel -> (CS net pin on the Q, slot x, wall side +1/-1)
CHANNELS = [
    # name, CS pin, slot x (enclosure frame), wall side (+1 = +y wall, -1 = -y)
    ('L1', 'D3', +125, +1),
    ('L2', 'D4', +85, +1),
    ('L3', 'D5', -85, +1),
    ('L4', 'D6', -125, +1),
    ('R1', 'D7', +85, -1),
    ('R2', 'D8', +125, -1),
    ('R3', 'D9', -125, -1),
    ('R4', 'A2', -85, -1),
]

FP_R0603 = 'Resistor_SMD:R_0603_1608Metric'
FP_C0603 = 'Capacitor_SMD:C_0603_1608Metric'
FP_C0805 = 'Capacitor_SMD:C_0805_2012Metric'
FP_TSSOP = 'Package_SO:TSSOP-16_4.4x5mm_P0.65mm'
FP_JST = 'Connector_JST:JST_XH_S3B-XH-SM4-TB_1x03-1MP_P2.50mm_Horizontal'
FP_HDR = 'Connector_PinHeader_2.54mm:PinHeader_1x%02d_P2.54mm_Vertical_SMD_Pin1Left'
FP_HOLE = 'MountingHole:MountingHole_2.7mm_M2.5'

# Orderable parts (value -> BOM data)
P = {
    'ADS1220': dict(value='ADS1220IPWR', mfr='Texas Instruments', mpn='ADS1220IPWR',
                    desc='24-bit 2 kSPS 4-ch delta-sigma ADC, PGA, SPI', pkg='TSSOP-16'),
    'R1k5': dict(value='1.5k 0.1% 25ppm', mfr='Susumu', mpn='RG1608P-152-B-T5',
                 desc='Resistor thin film 1.5 kOhm 0.1% 25 ppm/C 0.1 W', pkg='0603',
                 alt='Panasonic ERA-3AEB152V'),
    'R100': dict(value='100', mfr='Yageo', mpn='RC0603FR-07100RL',
                 desc='Resistor 100 Ohm 1% 0.1 W', pkg='0603'),
    'R33': dict(value='33', mfr='Yageo', mpn='RC0603FR-0733RL',
                desc='Resistor 33 Ohm 1% 0.1 W', pkg='0603'),
    'C100n': dict(value='100n', mfr='Murata', mpn='GRM188R71H104KA93D',
                  desc='Capacitor MLCC 100 nF 50 V X7R', pkg='0603'),
    'C10n': dict(value='10n C0G', mfr='Murata', mpn='GRM1885C1H103JA01D',
                 desc='Capacitor MLCC 10 nF 50 V C0G', pkg='0603'),
    'C1n': dict(value='1n C0G', mfr='Murata', mpn='GRM1885C1H102JA01D',
                desc='Capacitor MLCC 1 nF 50 V C0G', pkg='0603'),
    'C10u': dict(value='10u', mfr='Murata', mpn='GRM21BR61C106KE15L',
                 desc='Capacitor MLCC 10 uF 16 V X5R', pkg='0805'),
    'JST': dict(value='S3B-XH-SM4-TB', mfr='JST', mpn='S3B-XH-SM4-TB(LF)(SN)',
                desc='JST-XH 3-pin side-entry SMT header 2.5 mm', pkg='SMD'),
    'H6': dict(value='1x06 SMD male', mfr='Samtec', mpn='TSM-106-01-T-SV-P',
               desc='Header 1x6 2.54 mm SMT male, pick-and-place pad', pkg='SMD'),
    'H8': dict(value='1x08 SMD male', mfr='Samtec', mpn='TSM-108-01-T-SV-P',
               desc='Header 1x8 2.54 mm SMT male, pick-and-place pad', pkg='SMD'),
    'H10': dict(value='1x10 SMD male', mfr='Samtec', mpn='TSM-110-01-T-SV-P',
                desc='Header 1x10 2.54 mm SMT male, pick-and-place pad', pkg='SMD'),
}

V33 = '+3V3'
GND = 'GND'


def part(ref, kind, sym, fp, pins, **extra):
    d = dict(ref=ref, kind=kind, sym=sym, fp=fp, pins=pins)
    d.update(P[kind])
    d.update(extra)
    d['uuid'] = uid('sym', ref)
    return d


def build():
    parts = []
    for k, (name, cs_pin, slot_x, side) in enumerate(CHANNELS, start=1):
        S, A0, A1, REF, CS = (name + '_S', name + '_AIN0', name + '_AIN1',
                              name + '_REF', 'CS_' + name)
        drdy = 'DRDY' if name == 'L1' else None
        parts.append(part('U%d' % k, 'ADS1220', 'Analog_ADC:ADS1220xPW', FP_TSSOP, {
            '1': 'SCLK', '2': CS, '3': GND, '4': GND, '5': GND,
            '6': None, '7': None, '8': GND, '9': V33, '10': A1, '11': A0,
            '12': V33, '13': V33, '14': drdy, '15': 'MISO', '16': 'MOSI'},
            channel=name, role='adc'))
        parts.append(part('J%d' % k, 'JST', 'Connector_Generic:Conn_01x03', FP_JST,
                          {'1': V33, '2': GND, '3': S}, channel=name, role='jst'))
        r = lambda n: 'R%d%02d' % (k, n)
        c = lambda n: 'C%d%02d' % (k, n)
        parts += [
            part(r(1), 'R1k5', 'Device:R', FP_R0603, {'1': V33, '2': REF}, channel=name, role='ra'),
            part(r(2), 'R1k5', 'Device:R', FP_R0603, {'1': REF, '2': GND}, channel=name, role='rb'),
            part(r(3), 'R100', 'Device:R', FP_R0603, {'1': S, '2': A0}, channel=name, role='rs0'),
            part(r(4), 'R100', 'Device:R', FP_R0603, {'1': REF, '2': A1}, channel=name, role='rs1'),
            part(c(1), 'C100n', 'Device:C', FP_C0603, {'1': V33, '2': GND}, channel=name, role='cavdd'),
            part(c(2), 'C100n', 'Device:C', FP_C0603, {'1': V33, '2': GND}, channel=name, role='cdvdd'),
            part(c(3), 'C100n', 'Device:C', FP_C0603, {'1': V33, '2': GND}, channel=name, role='cref'),
            part(c(4), 'C10n', 'Device:C', FP_C0603, {'1': A0, '2': A1}, channel=name, role='cdiff'),
            part(c(5), 'C1n', 'Device:C', FP_C0603, {'1': A0, '2': GND}, channel=name, role='ccm0'),
            part(c(6), 'C1n', 'Device:C', FP_C0603, {'1': A1, '2': GND}, channel=name, role='ccm1'),
            part(c(7), 'C10u', 'Device:C', FP_C0805, {'1': V33, '2': GND}, channel=name, role='cbulk'),
        ]

    # UNO R3 headers. Pin k of each header, Uno-frame x (mm), y (mm), Q pin name.
    hdr = {
        'J9': ('H8', 8, 2.54, [27.94 + 2.54 * i for i in range(8)],
               ['NC', 'IOREF', 'RESET', '3V3', '5V', 'GND', 'GND', 'VIN']),
        'J10': ('H6', 6, 2.54, [50.8 + 2.54 * i for i in range(6)],
                ['A0', 'A1', 'A2', 'A3', 'A4', 'A5']),
        'J11': ('H8', 8, 50.8, [63.5 - 2.54 * i for i in range(8)],
                ['D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7']),
        'J12': ('H10', 10, 50.8, [41.66 - 2.54 * i for i in range(10)],
                ['D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'GND', 'AREF', 'SDA', 'SCL']),
    }
    qnet = {'3V3': V33, 'GND': GND, 'D2': 'DRDY', 'D11': 'MOSI', 'D12': 'MISO',
            'D13': 'SCLK_Q'}
    for name, cs_pin, _, _ in CHANNELS:
        qnet[cs_pin] = 'CS_' + name
    headers = {}
    for ref, (kind, n, uy, uxs, names) in hdr.items():
        pins = {str(i + 1): qnet.get(names[i]) for i in range(n)}
        parts.append(part(ref, kind, 'Connector_Generic:Conn_01x%02d' % n, FP_HDR % n, pins,
                          role='header', qpins=names))
        headers[ref] = (uy, uxs)
    parts += [
        part('R1', 'R33', 'Device:R', FP_R0603, {'1': 'SCLK_Q', '2': 'SCLK'}, role='rsclk'),
        part('C1', 'C10u', 'Device:C', FP_C0805, {'1': V33, '2': GND}, role='cin'),
        part('C2', 'C100n', 'Device:C', FP_C0603, {'1': V33, '2': GND}, role='cin2'),
    ]
    return parts, headers


UNO_ORIGIN = (-34.29, -26.67)   # Uno lower-left corner in the enclosure frame


def nets(parts):
    out = set()
    for p in parts:
        for n in p['pins'].values():
            if n:
                out.add(n)
    return sorted(out)
