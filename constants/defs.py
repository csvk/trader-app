SELL = -1
BUY = 1
NONE = 0

ERROR_LOG = "error"
MAIN_LOG = "main"

API_CREDS_FILE = './api/api_creds.json'
DATA_PATH = "./data/"
INSTR_FILE = "instruments.json"

INSTR_KEYS = dict(
        type=None,
        displayName=None,
        pipLocation=None,
        displayPrecision=None,
        tradeUnitsPrecision=None,
        minimumTradeSize=float,
        maximumTrailingStopDistance=float,
        minimumTrailingStopDistance=float,
        maximumPositionSize=float,
        maximumOrderUnits=float,
        marginRate=float
    
)