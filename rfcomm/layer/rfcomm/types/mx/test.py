from layer.rfcomm.const import MX_TYPE

class TEST:
    def name():
        return 'TEST'

    @classmethod
    def gen(cls, payload=None, is_response=False, **kwargs):
        test_data = payload if payload is not None else b''
        
        # Base type for TEST command is 0x23 (0b00100011)
        base_type = MX_TYPE.MX_TEST
        
        if is_response:
            # A response flips the C/R bit from 1 to 0.
            # 0b00100011 -> 0b00100001 (0x21)
            type_field = base_type & ~0b00000010 
        else:
            # A command uses the type as-is.
            type_field = base_type

        length_field = (len(test_data) << 1) | 1
        return bytes([type_field, length_field]) + test_data