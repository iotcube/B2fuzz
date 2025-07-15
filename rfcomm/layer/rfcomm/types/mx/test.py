# In rfcomm/layer/rfcomm/types/mx/test.py

from layer.rfcomm.const import MX_TYPE

class TEST:
    """
    TEST MX command payload generator class.
    """
    def name():
        """Return TEST command name"""
        return 'TEST'

    @classmethod
    def gen(cls, payload=None, **kwargs):
        """
        Generates the inner payload for a TEST multiplexer command.
        This consists of [type, length, data...].

        Parameters
        ----------
        - payload: [bytes] The test pattern data. If None, an empty payload is used.
        - **kwargs: Catches unused arguments for compatibility.

        Returns
        ----------
        - [bytes] The complete TEST command payload for insertion into a UIH frame.
        """
        # Set a default empty payload if none is provided.
        test_data = payload if payload is not None else b''
        
        # The command payload consists of its type, its length, and its data.
        # This uses the constant from const.py DIRECTLY, without incorrect modification.
        type_field = MX_TYPE.MX_TEST
        length_field = (len(test_data) << 1) | 1  # Length of the test data
        
        return bytes([type_field, length_field]) + test_data