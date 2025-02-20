from random import randint, randrange, choices, choice
RFCOMM_PSM = 0x3

crc_table: list = [
            0x00, 0x91, 0xE3, 0x72, 0x07, 0x96, 0xE4, 0x75,
            0x0E, 0x9F, 0xED, 0x7C, 0x09, 0x98, 0xEA, 0x7B,
            0x1C, 0x8D, 0xFF, 0x6E, 0x1B, 0x8A, 0xF8, 0x69,
            0x12, 0x83, 0xF1, 0x60, 0x15, 0x84, 0xF6, 0x67,
            0x38, 0xA9, 0xDB, 0x4A, 0x3F, 0xAE, 0xDC, 0x4D,
            0x36, 0xA7, 0xD5, 0x44, 0x31, 0xA0, 0xD2, 0x43,
            0x24, 0xB5, 0xC7, 0x56, 0x23, 0xB2, 0xC0, 0x51,
            0x2A, 0xBB, 0xC9, 0x58, 0x2D, 0xBC, 0xCE, 0x5F,
            0x70, 0xE1, 0x93, 0x02, 0x77, 0xE6, 0x94, 0x05,
            0x7E, 0xEF, 0x9D, 0x0C, 0x79, 0xE8, 0x9A, 0x0B,
            0x6C, 0xFD, 0x8F, 0x1E, 0x6B, 0xFA, 0x88, 0x19,
            0x62, 0xF3, 0x81, 0x10, 0x65, 0xF4, 0x86, 0x17,
            0x48, 0xD9, 0xAB, 0x3A, 0x4F, 0xDE, 0xAC, 0x3D,
            0x46, 0xD7, 0xA5, 0x34, 0x41, 0xD0, 0xA2, 0x33,
            0x54, 0xC5, 0xB7, 0x26, 0x53, 0xC2, 0xB0, 0x21,
            0x5A, 0xCB, 0xB9, 0x28, 0x5D, 0xCC, 0xBE, 0x2F,
            0xE0, 0x71, 0x03, 0x92, 0xE7, 0x76, 0x04, 0x95,
            0xEE, 0x7F, 0x0D, 0x9C, 0xE9, 0x78, 0x0A, 0x9B,
            0xFC, 0x6D, 0x1F, 0x8E, 0xFB, 0x6A, 0x18, 0x89,
            0xF2, 0x63, 0x11, 0x80, 0xF5, 0x64, 0x16, 0x87,
            0xD8, 0x49, 0x3B, 0xAA, 0xDF, 0x4E, 0x3C, 0xAD,
            0xD6, 0x47, 0x35, 0xA4, 0xD1, 0x40, 0x32, 0xA3,
            0xC4, 0x55, 0x27, 0xB6, 0xC3, 0x52, 0x20, 0xB1,
            0xCA, 0x5B, 0x29, 0xB8, 0xCD, 0x5C, 0x2E, 0xBF,
            0x90, 0x01, 0x73, 0xE2, 0x97, 0x06, 0x74, 0xE5,
            0x9E, 0x0F, 0x7D, 0xEC, 0x99, 0x08, 0x7A, 0xEB,
            0x8C, 0x1D, 0x6F, 0xFE, 0x8B, 0x1A, 0x68, 0xF9,
            0x82, 0x13, 0x61, 0xF0, 0x85, 0x14, 0x66, 0xF7,
            0xA8, 0x39, 0x4B, 0xDA, 0xAF, 0x3E, 0x4C, 0xDD,
            0xA6, 0x37, 0x45, 0xD4, 0xA1, 0x30, 0x42, 0xD3,
            0xB4, 0x25, 0x57, 0xC6, 0xB3, 0x22, 0x50, 0xC1,
            0xBA, 0x2B, 0x59, 0xC8, 0xBD, 0x2C, 0x5E, 0xCF
]

class RFCOMM_CONTROL:
    RC_CONTROL_SABM = 0b00111111 # P/F flag to 1
    RC_CONTROL_UA = 0b01110011 # P/F flag to 1
    RC_CONTROL_DM = 0b00001111
    RC_CONTROL_DISC = 0b01000011
    RC_CONTROL_UIH = 0b11101111


class MX_TYPE:
    MX_PN = 0b10000011
    MX_TEST = 0b00100011
    MX_MSC = 0b11100011
    MX_FCON = 0b10100011
    MX_FCOFF = 0b01100011
    MX_RPN = 0b10010011
    MX_RLS = 0b01010011
    MX_NSC = 0b00010011


def xor(a, b):
    return bytes(_a ^ _b for _a, _b in zip(a, b))

# len: 입력값의 길이 (단위: 바이트)
def bitflip(p: int, l: int) -> int:
    assert 0 <= p <= ((1 << (l * 8)) - 1) and l <= 2

    op = randint(0, 2 if l == 1 else 3)
    result = p.to_bytes(l, 'big')

    if op == 0:
        key = b'\xff' * l
    
    elif op == 1:
        if l == 1:
            key = b'\x81'
        else:
            key = b'\x80' + b'\x00' * (l - 2) + b'\x01'

    # 4/1
    elif op == 2:
        if l == 1:
            key = b'\xA5'
        else:
            key = b'\xA0' + b'\x00' * (l - 2) + b'\x05'

    # 16/8
    elif op == 3:
        assert l == 2
        key = b'\xff\x00'

    else:
        assert False

    result = xor(result, key)

    result = int.from_bytes(result, byteorder='big')
    return result

def arithmetic(p: int, l: int) -> int:
    assert 0 <= p <= ((1 << (l * 8)) - 1) and l <= 2

    op = randint(0, 0 if l == 1 else 1)
    inc_or_dec = randint(0, 1)

    # 8/8
    if op == 0:
        if l == 1:
            if inc_or_dec:
                p += 1
            else:
                p -= 1
            p = p % ((1 << (l * 8)))
        else:
            hb = p // 0x100
            lb = p % 0x100
            if inc_or_dec:
                hb += 1
                lb += 1
            else:
                hb -= 1
                lb -= 1
            hb = hb % ((1 << ((l - 1) * 8)))
            p = (hb << ((l - 1) * 8)) | lb

    # 16/8
    elif op == 1:
        if inc_or_dec:
            p += 1
        else:
            p -= 1
        p = p % (1 << (l * 8))
    else:
        assert False

    return p

def random_byte(p: int, l: int) -> int:
    assert 0 <= p <= ((1 << (l * 8)) - 1) and l <= 2
    
    if l == 1:
        p = randrange(0x00, 0x100) 

    elif l == 2:
        hb = p // 0x100
        lb = p % 0x100

        op = randint(0, 2)

        # randomize hb
        if op == 0:
            p = (randrange(0x00, 0x100) << 8) | lb
        # randomize lb
        elif op == 1:
            p = (hb << 8) | (randrange(0x00, 0x100))
        else:
            p = randrange(0x00, 0x10000)

    else:
        assert False

    return p

def zero_padding(p: int, l: int) -> int:
    assert 0 <= p <= ((1 << (l * 8)) - 1) and l <= 2
    return 0

def crossover(p: int, l: int) -> int:
    assert 0 <= p <= ((1 << (l * 8)) - 1) and l <= 2
    if l == 1:
        hhb = p // 0x10
        lhb = p % 0x10
        p = (lhb << 4) | hhb
    else:
        hb = p // 0x100
        lb = p % 0x100
        p = (lb << 8) | hb
    return p


def gen_param(origin, bytelen, condition):
    """
    AFL mutator

    Parameters
    ----------
    - origin: [bytes] original bytes
    - bytelen: [int] bytes length to make
    - condition: [tuple] ([int] under bound, [int] upper bound)
    
    Returns
    ----------
    - [bytes] mutates bytes

    """

    # [1] AFL mutation operation
    opers = [bitflip, arithmetic, random_byte, zero_padding, crossover]
    
    # [2] select random operation
    oper_idx = randrange(0, len(opers))

    # [3] mutate original bytes
    result = opers[oper_idx](origin, bytelen)
    
    # [4] select the bytes meets condition
    while (1):
        oper_idx = randrange(0, len(opers))
        result = opers[oper_idx](origin, bytelen)
        if (condition[0] <= result < condition[1]):
            break
    return result
