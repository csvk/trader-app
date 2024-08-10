import requests
import pandas as pd
import json
import constants.defs as defs
from api.api_creds import ApiCreds

from dateutil import parser
from datetime import datetime as dt
from api.api_price import ApiPrice
from api.open_trade import OpenTrade

class OandaApi:
    PATH = defs.DATA_PATH
    INSTR_FILE = defs.INSTR_FILE

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {ApiCreds.API_KEY}",
            "Content-Type": "application/json"
        })
        self.download_account_instruments()

    def make_request(self, url, verb='get', code=200, params=None, data=None, headers=None):
        full_url = f"{ApiCreds.OANDA_URL}/{url}"

        if data is not None:
            data = json.dumps(data)

        try:
            response = None
            if verb == "get":
                response = self.session.get(full_url, params=params, data=data, headers=headers)
            if verb == "post":
                response = self.session.post(full_url, params=params, data=data, headers=headers)
            if verb == "put":
                response = self.session.put(full_url, params=params, data=data, headers=headers)
            
            if response == None:
                return False, {'error': 'verb not found'}

            if response.status_code == code:
                return True, response.json()
            else:
                return False, response.json()
            
        except Exception as error:
            return False, {'Exception': error}

    def get_account_ep(self, ep, keys):
        assert type(keys) == list or type(keys) == str, 'API endpoint key can be string or list of strings'

        if type(keys) != list:
            keys = [keys]

        url = f"accounts/{ApiCreds.ACCOUNT_ID}/{ep}"
        ok, data = self.make_request(url)

        if ok == True:
            missing_keys = [key for key in keys if key not in data]
            if len(missing_keys) == 0:
                ret_val = data[keys(0)] if len(keys) == 0 else {k: data[k] for k in keys}
                return ok, ret_val
            else:
                present_keys = [key for key in keys if key not in missing_keys]
                return False, {k: data[k] for k in present_keys}
        else:
            return False, None

    def get_account_summary(self):
        return self.get_account_ep("summary", "account")

    def get_account_instruments(self):
        return self.get_account_ep("instruments", "instruments")
    
    def download_account_instruments(self):
        attempts = 0
        while attempts < 3:
            ok, data = self.get_account_instruments()
            if ok == True and data is not None:
                break
            attempts += 1

        if data is not None and len(data) != 0:
            self.instruments = {d['name']: d for d in data['instruments']}
            file = f"{self.PATH}/{self.INSTR_FILE}"
            with open(file, "w") as f:
                f.write(json.dumps(self.instruments, indent=2))
        else:
            raise 'Instruments download error'
        
    def get_instrument_settings(self, instruments):
        return {i: self.instruments[i] for i in instruments}
    
    def get_last_transaction_id(self):
        ok, data = self.get_account_ep("summary", "lastTransactionID")

        if ok == True:
            return ok, data["lastTransactionID"]
        else:
            return False, None
        
    def get_state_changes(self, last_transaction_id):
        url = f"accounts/{ApiCreds.ACCOUNT_ID}/changes?sinceTransactionID={last_transaction_id}"
        ok, data = self.make_request(url)

        changes = data["changes"] if "changes" in data else None
        state = data["state"] if "state" in data else None
        lastTransactionID = data["lastTransactionID"] if "lastTransactionID" in data else None

        return ok, changes, state, lastTransactionID

    def fetch_candles(self, pair_name, count=10, granularity="H1",
                            price="MBA", date_f=None, date_t=None):
        url = f"instruments/{pair_name}/candles"
        params = dict(
            granularity = granularity,
            price = price
        )

        if date_f is not None and date_t is not None:
            date_format = "%Y-%m-%dT%H:%M:%SZ"
            params["from"] = dt.strftime(date_f, date_format)
            params["to"] = dt.strftime(date_t, date_format)
        else:
            params["count"] = count

        ok, data = self.make_request(url, params=params)
    
        if ok == True and 'candles' in data:
            return ok, data['candles']
        else:
            return False, None

    def get_candles_df(self, pair_name, **kwargs):

        ok, data = self.fetch_candles(pair_name, **kwargs)

        if not ok or data is None:
            return False, None
        # if len(data) == 0:
        #     return pd.DataFrame()
        
        prices = ['mid', 'bid', 'ask']
        ohlc = ['o', 'h', 'l', 'c']
        
        final_data = []
        for candle in data:
            if candle['complete'] == False:
                continue
            new_dict = {}
            new_dict['time'] = parser.parse(candle['time'])
            new_dict['volume'] = candle['volume']
            for p in prices:
                if p in candle:
                    for o in ohlc:
                        new_dict[f"{p}_{o}"] = float(candle[p][o])
            final_data.append(new_dict)
        df = pd.DataFrame.from_dict(final_data)
        return True, df

    def last_complete_candle(self, pair_name, granularity):
        ok, df = self.get_candles_df(pair_name, granularity=granularity, count=10)
        if ok == True: 
            return ok, df.iloc[-1].time
        else:
            return False, None
        
    def web_api_candles(self, pair_name, granularity, count):
        df = self.get_candles_df(pair_name, granularity=granularity, count=count)
        if df.shape[0] == 0:
            return None

        cols = ['time', 'mid_o', 'mid_h', 'mid_l', 'mid_c']
        df = df[cols].copy()

        df['time'] = df.time.dt.strftime("%y-%m-%d %H:%M")

        return df.to_dict(orient='list')
        
    def place_market_order(self, instrument, units):

        url = f"accounts/{ApiCreds.ACCOUNT_ID}/orders"

        data = dict(
            order=dict(
                units=str(units),
                instrument=instrument,
                type="MARKET"
            )
        )

        ok, response = self.make_request(url, verb="post", data=data, code=201)

        if ok == True and 'orderFillTransaction' in response:
            return ok, response['orderFillTransaction']
        else:
            return False, None
        
    def place_take_profit_order(self, instrument, units):

        url = f"accounts/{ApiCreds.ACCOUNT_ID}/orders"

        data = dict(
            order=dict(
                units=str(units),
                instrument=instrument,
                type="MARKET"
            )
        )

        ok, response = self.make_request(url, verb="post", data=data, code=201)

        if ok == True and 'orderFillTransaction' in response:
            return ok, response['orderFillTransaction']
        else:
            return False, None
        
    

    def place_trade(self, instrument: dict, units: float, direction: int,
                        stop_loss: float=None, take_profit: float=None):

        url = f"accounts/{ApiCreds.ACCOUNT_ID}/orders"

        # instrument = ic.instruments_dict[pair_name]
        units = round(units, instrument.tradeUnitsPrecision)

        if direction == defs.SELL:
            units = units * -1        

        data = dict(
            order=dict(
                units=str(units),
                instrument=instrument.name,
                type="MARKET"
            )
        )

        if stop_loss is not None:
            sld = dict(price=str(round(stop_loss, instrument.displayPrecision)))
            data['order']['stopLossOnFill'] = sld

        if take_profit is not None:
            tpd = dict(price=str(round(take_profit, instrument.displayPrecision)))
            data['order']['takeProfitOnFill'] = tpd

        ok, response = self.make_request(url, verb="post", data=data, code=201)

        if ok == True and 'orderFillTransaction' in response:
            return ok, response['orderFillTransaction']['id']
        else:
            return False, None
            
    def close_trade(self, trade_id):
        url = f"accounts/{ApiCreds.ACCOUNT_ID}/trades/{trade_id}/close"
        ok, _ = self.make_request(url, verb="put", code=200)
        return ok

    def get_open_trade(self, trade_id):
        url = f"accounts/{ApiCreds.ACCOUNT_ID}/trades/{trade_id}"
        ok, response = self.make_request(url)

        if ok == True and 'trade' in response:
            return ok, OpenTrade(response['trade'])
        else:
            return False, None

    def get_open_trades(self):
        url = f"accounts/{ApiCreds.ACCOUNT_ID}/openTrades"
        ok, response = self.make_request(url)

        if ok == True and 'trades' in response:
            # return ok, [OpenTrade(x) for x in response['trades']]
            return response["trades"]
        else:
            return False, list()
        
    def get_pending_orders(self):
        url = f"accounts/{ApiCreds.ACCOUNT_ID}/pendingOrders"
        ok, response = self.make_request(url)

        if ok == True and 'orders' in response:
            return response["orders"]
        else:
            return False, list()
        
    def get_prices(self, instruments_list):
        url = f"accounts/{ApiCreds.ACCOUNT_ID}/pricing"

        params = dict(
            instruments=','.join(instruments_list),
            includeHomeConversions=True
        )

        ok, response = self.make_request(url, params=params)

        if ok == True and 'prices' in response and 'homeConversions' in response:
            return ok, [ApiPrice(x, response['homeConversions']) for x in response['prices']]
        else:
            return False, list()













