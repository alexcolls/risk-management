
from oandapyV20 import API as oapi
import oandapyV20.endpoints.instruments as instruments
import oandapyV20.endpoints.pricing as pricing

import pandas as pd
from datetime import datetime as dt
import time

import pygsheets

### Google Sheets Connection ###

GSjson = 'C:\X-Projects\Python\TradingTeam\dep\local\OandaEurope\GoogleSheet\GS_main.json'
GSheet = 'OandaEurope'
gs = pygsheets.authorize(service_file=GSjson)
sh = gs.open(GSheet); gsPrices = sh[9]

Token = 'ea74153c2aba5b6e58714d57b3601602-7669b039c81edcc9b1ec2e4c8fadf2fa'
AccountID = '101-004-9922005-009'

syms = ['AU200_AUD','CN50_USD','EU50_EUR','FR40_EUR','DE30_EUR','HK33_HKD','IN50_USD','JP225_USD','NL25_EUR','SG30_SGD','TWIX_USD','UK100_GBP','NAS100_USD','US2000_USD','SPX500_USD','US30_USD','DE10YB_EUR','UK10YB_GBP','USB10Y_USD','USB02Y_USD','USB05Y_USD','USB30Y_USD','BCO_USD','WTICO_USD','NATGAS_USD','CORN_USD','SOYBN_USD','SUGAR_USD','WHEAT_USD','XCU_USD','XPT_USD','XPD_USD','XAU_USD','XAG_USD','XAU_AUD','XAU_CAD','XAU_CHF','XAU_EUR','XAU_GBP','XAU_HKD','XAU_JPY','XAU_NZD','XAU_SGD','XAU_XAG','XAG_AUD','XAG_CAD','XAG_CHF','XAG_EUR','XAG_GBP','XAG_HKD','XAG_JPY','XAG_NZD','XAG_SGD','AUD_USD','EUR_USD','GBP_USD','NZD_USD','USD_CAD','USD_CHF','USD_HKD','USD_JPY','USD_SGD','AUD_CAD','AUD_CHF','AUD_HKD','AUD_JPY','AUD_NZD','AUD_SGD','CAD_CHF','CAD_HKD','CAD_JPY','CAD_SGD','CHF_HKD','CHF_JPY','EUR_AUD','EUR_CAD','EUR_CHF','EUR_GBP','EUR_HKD','EUR_JPY','EUR_NZD','EUR_SGD','GBP_AUD','GBP_CAD','GBP_CHF','GBP_HKD','GBP_JPY','GBP_NZD','GBP_SGD','HKD_JPY','NZD_CAD','NZD_CHF','NZD_HKD','NZD_JPY','NZD_SGD','SGD_CHF','SGD_HKD','SGD_JPY','EUR_DKK','EUR_NOK','EUR_SEK','USD_DKK','USD_NOK','USD_SEK','CHF_ZAR','EUR_CZK','EUR_HUF','EUR_PLN','EUR_TRY','EUR_ZAR','GBP_PLN','GBP_ZAR','TRY_JPY','USD_CNH','USD_CZK','USD_HUF','USD_INR','USD_MXN','USD_PLN','USD_SAR','USD_THB','USD_TRY','USD_ZAR','ZAR_JPY']

oanda_api = oapi(access_token=Token)

Prices = 0

def gvPrices():
    global Prices
    symStr = ''
    for sym in syms:
        symStr = symStr+','+sym
    params = {'instruments': symStr[1:]}
    request = pricing.PricingInfo(accountID=AccountID, params=params)
    api_request = oanda_api.request(request)
    r = pd.DataFrame(request.response['prices'])
    Prices = pd.DataFrame()
    Prices['Symbol'] = r['instrument']
    Prices['Bid'] = r['closeoutBid'].astype(float)
    Prices['Ask'] = r['closeoutAsk'].astype(float)
    Prices['Spread'] = round((Prices['Ask']/Prices['Bid']-1)*100,3)
    Prices['Mid'] = round((Prices['Bid']+Prices['Ask'])/2, 5)
    Prices = Prices.set_index('Symbol')
    for sym in syms:
        Prices['Spread'][sym] = str(Prices['Spread'][sym]) + '%'

DailyCandles = 0
params = {'granularity': 'D', 'count': '400'}

def gvDailyCandles(Symbol, params):
    global DailyCandles
    request = instruments.InstrumentsCandles(instrument=Symbol, params=params)
    api_request = oanda_api.request(request)
    df = pd.DataFrame(request.response['candles'])
    Len = len(df); t, o, h, l, c, r, v, b = [], [], [], [], [], [], [], []
    for i in range(Len):
        if df['complete'][i]:
            t.append(dt.strptime(df['time'][i][:10],'%Y-%m-%d'))
            o.append(float(df['mid'][i]['o']))
            h.append(float(df['mid'][i]['h']))
            l.append(float(df['mid'][i]['l']))
            c.append(float(df['mid'][i]['c']))
            r.append(float(df['mid'][i]['c'])/float(df['mid'][i]['o'])-1)
            v.append(float(df['mid'][i]['h'])/float(df['mid'][i]['l'])-1)
            b.append(int(df['volume'][i]))
    DailyCandles = pd.DataFrame({'Date':t,'Open':o,'High':h,'Low':l,'Close':c,'Return':r,'Volatility':v,'Volume':b})
    DailyCandles = DailyCandles.set_index('Date')

now = dt.now()
def YtD():   
    for i in range(1,9):
        date = str(now.year)+'-'+'01-0'+str(i)
        try:
            return float(DailyCandles['Open'][date])
        except:
            continue

def StD():
    month = now.month
    if month > 6:
        month = '-07-0'
    else:
        month = '-01-0'
    for i in range(1, 9):
        date = str(now.year)+month+str(i)
        try:
            return float(DailyCandles['Open'][date])
        except:
            continue

def QtD():
    month = now.month
    if month < 4:
        month = '-01-0'
    elif month < 7:
        month = '-04-0'
    elif month < 10:
        month = '-07-0'
    else:
        month = '-10-0'
    for i in range(1, 9):
        date = str(now.year)+month+str(i)
        try:
            return float(DailyCandles['Open'][date])
        except:
            continue

def MtD():
    for i in range(1, 9):
        date = str(now.year)+'-'+str(now.month)+'-0'+str(i)
        try:
            return float(DailyCandles['Open'][date])
        except:
            continue

def WtD():
    df = DailyCandles.tail(5)
    df['Weekday'] = df.index.weekday
    df = df.set_index('Weekday')
    for i in range(5):
        try:
            return df['Open'][i]
        except:
            continue

def DtD():
    return DailyCandles['Open'].iloc[-1]

rTD = pd.DataFrame(index=syms,columns=['DTD','WTD','MTD','QTD','STD','YTD'])
vTD = pd.DataFrame(index=syms,columns=['DTD','WTD','MTD','QTD','STD','YTD'])

def gvTD():
    global rTD
    for sym in syms:
        gvDailyCandles(sym,params)
        Price = float(Prices['Mid'][sym])
        rTD['DTD'][sym] = str(round((Price/DtD()-1)*100, 2))+'%'
        #rTD['WTD'][sym] = str(round((Price/WtD()-1)*100, 2))+'%'
        #rTD['MTD'][sym] = str(round((Price/MtD()-1)*100, 2))+'%'
        #rTD['QTD'][sym] = str(round((Price/QtD()-1)*100, 2))+'%'
        #rTD['STD'][sym] = str(round((Price/StD()-1)*100, 2))+'%'
        #rTD['YTD'][sym] = str(round((Price/YtD()-1)*100, 2))+'%'
    
while True:
    gvPrices()
    print(Prices)
    gsPrices.set_dataframe(Prices, (2,2))
    gvTD()
    gsPrices.set_dataframe(rTD, (2,7))
    time.sleep(10)
