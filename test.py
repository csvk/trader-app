from api.oanda_api import OandaApi

api = OandaApi()

response = api.web_api_candles('GBP_JPY', 'M1', 5)

print(response)