from layer.rfcomm.const import crc_table

def calc_fcs(len, buf):
    fcs = 0xFF
    for i in range(len):
        fcs = crc_table[fcs ^ buf[i]]
    return (0xff - fcs)

def rfc_check_fcs(len, buf, received_fcs):
    fcs = 0xff
    for i in range(len):
        fcs = crc_table[fcs ^ buf[i]]
    fcs = crc_table[fcs ^ received_fcs]
    return fcs == 0xcf