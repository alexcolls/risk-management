
### Risk Management Trader ###

import oandapyV20
import oandapyV20.endpoints.trades as api_trades
import oandapyV20.endpoints.transactions as api_trans
import oandapyV20.endpoints.pricing as api_pricing
import oandapyV20.endpoints.orders as api_orders
import pandas as pd
from math import isnan
from sqlalchemy import create_engine
import datetime as dt
import time

pd.set_option('mode.chained_assignment', None)

configOanda = open('C:\X-Projects\Python\TradingTeam\dev\RiskManagement.config','r')
GSheet, Token, accountID, *rest = configOanda.read().splitlines()
configOanda.close()
configGS = 'C:\X-Projects\Python\TradingTeam\dev\RiskManagement.json'
oanda_api = oandapyV20.API(access_token=Token)

balance = 100000
currency = 'EUR'
tf = 'D1'
risk = 0.05
table = "AvgVolatilities"


def _trades(accountID):
    api =  api_trades.OpenTrades(accountID)
    req = pd.DataFrame(oanda_api.request(api)['trades'])
    trades = pd.DataFrame(columns=['id','symbol','price','size','tp','sl','datetime','tick'])
    if len(req) > 0:
        trades['id'] = req['id']
        trades['symbol'] = req['instrument']
        trades['price'] = req['price']
        trades['size'] = req['initialUnits'].astype(int)
        tp = 0; sl = 0
        try:
            tp = req['takeProfitOrder']
        except:
            pass
        try:
            sl = req['stopLossOrder']
        except:
            pass
        trades['tp'] = tp            
        trades['sl'] = sl
        trades['datetime'] = req['openTime']
        trades['tick'] = 0
        for i in range(len(trades)):
            if type(trades['tp'][i]) is dict:
                trades['tp'][i] = trades['tp'][i]['price']
            else:
                trades['tp'][i] = 0
            if type(trades['sl'][i]) is dict:
                trades['sl'][i] = trades['sl'][i]['price']
            else:
                trades['sl'][i] = 0
            trades['datetime'][i] = dt.datetime.strptime(req['openTime'][i].split('.')[0],"%Y-%m-%dT%H:%M:%S")
            if '.' in trades['price'][i]:
                trades['tick'][i] = len(str(trades['price'][i]).split('.')[1])
    return trades

def _ntrades(trades):
    return len(trades)

def _syms(trades):
    return trades['symbol'].unique()

def _betas(table):
    db = create_engine('mysql+pymysql://aco:Forex2015!@35.242.173.232/OandaEurope_Statistics')
    query = "SELECT * FROM " + table
    betas = pd.read_sql(query, db.connect())
    betas = betas.set_index('Symbol')
    betas = betas.astype(float)
    betas = betas.T
    return betas

def _setTPSL(betas,trades):
    TP = betas[0:5].mean()
    SL = betas[10:15].mean()
    message = []
    for i in range(len(trades)):
        if trades['tp'][i] == 0 or trades['sl'][i] == 0:
            if trades['size'][i] > 0:
                tp = round(float(trades['price'][i])*(1+TP[trades['symbol'][i]]/100),trades['tick'][i])
                sl = round(float(trades['price'][i])*(1-SL[trades['symbol'][i]]/100),trades['tick'][i])
            elif trades['size'][i] < 0:
                tp = round(float(trades['price'][i])*(1-TP[trades['symbol'][i]]/100),trades['tick'][i])
                sl = round(float(trades['price'][i])*(1+SL[trades['symbol'][i]]/100),trades['tick'][i])
            Data =  { "takeProfit": { "timeInForce": "GTC", "price": str(tp) },
                      "stopLoss":   { "timeInForce": "GTC", "price": str(sl) } }
            CRCDO = api_trades.TradeCRCDO(accountID=accountID,tradeID=trades['id'][i],data=Data)
            message.append(oanda_api.request(CRCDO))
    return message

def _quotes(syms):
    symStr = ''
    for sym in syms:
        symStr = symStr+','+sym
    params = {'instruments': symStr[1:]}
    api = api_pricing.PricingInfo(accountID=accountID, params=params)
    req = pd.DataFrame(oanda_api.request(api)['prices'])
    quotes = pd.DataFrame()
    quotes['symbol'] = req['instrument']
    quotes['bid'] = req['closeoutBid']
    quotes['ask'] = req['closeoutAsk']
    quotes = quotes.set_index('symbol')
    return quotes

def _mids(syms):
    quotes = _quotes(syms)
    mids = round((quotes['bid'].astype(float)+quotes['ask'].astype(float))/2, 5)
    return list(mids)

def _stats(accountID):
    api = api_trans.TransactionsSinceID(accountID=accountID, params={"id":1000})
    req = pd.DataFrame(oanda_api.request(api)['transactions'])
    req = req[req.type == 'ORDER_FILL']
    fills = pd.DataFrame(columns=['symbol','price','size','long','short'])
    fills['symbol'] = list(req['instrument'])
    fills['price'] = list(req['price'].astype(float))
    fills['size'] = list(req['units'].astype(int))
    for i in range(len(fills)):
        if fills['size'][i] < 0:
            fills['short'][i] = fills['price'][i]
        else:
            fills['long'][i] = fills['price'][i]
    stats = pd.DataFrame(columns=['symbol','price','long','short','eff'])
    stats['symbol'] = fills['symbol'].unique()
    stats['price'] = _mids(stats['symbol'])
    fills = fills.set_index('symbol')
    for i in range(len(stats)):
        if type(fills['long'][stats['symbol'][i]]) is float:
            if pd.notna(fills['long'][stats['symbol'][i]]):
                stats['long'][i] = round((stats['price'][i]/fills['long'][stats['symbol'][i]]-1)*100,2)
        else:
            stats['long'][i] = round((stats['price'][i]/fills['long'][stats['symbol'][i]].mean()-1)*100,2)
        if type(fills['short'][stats['symbol'][i]]) is float:
            if pd.notna(fills['long'][stats['symbol'][i]]):
                stats['short'][i] = round((fills['short'][stats['symbol'][i]]/stats['price'][i]-1)*100,2)
        else:
            stats['short'][i] = round((fills['short'][stats['symbol'][i]].mean()/stats['price'][i]-1)*100,2)
    stats = stats.fillna(0)
    for i in range(len(stats)):
        if stats['long'][i] > 0:
            stats['eff'][i] += 1
        if stats['short'][i] > 0:
            stats['eff'][i] += 1
    return stats

def _conf(stats):
    conf = round(stats['eff'].sum()/(len(stats)*2),2)
    return conf

def _corrs(tf):
    db = create_engine('mysql+pymysql://aco:Forex2015!@35.242.173.232/OandaEurope_Correlations')
    dbConnection = db.connect()
    query = "SELECT * FROM " + tf
    corrs = pd.read_sql(query, dbConnection)
    corrs = corrs.set_index('Symbol')
    return corrs

def _tradescorr(trades,corrs):
    trades_grouped = trades.groupby(['symbol']).mean()
    trades_grouped['dir'] = pd.np.where(trades_grouped['size'] > 0, 1, -1)
    tradescorr = pd.DataFrame(columns=['symbol','dir','prtfcorr','corrs'])
    tradescorr['symbol'] = trades_grouped.index
    tradescorr = tradescorr.set_index('symbol')
    tradescorr['dir'] = trades_grouped['dir']
    for x in tradescorr.index:
        tradescorr['corrs'][x] = []
        for y in tradescorr.index:
            if x != y:
                xy = float(corrs[x][y])
                if tradescorr['dir'][x] == tradescorr['dir'][y]:
                    tradescorr['corrs'][x].append(xy)
                else:
                    tradescorr['corrs'][x].append(-xy)
        tradescorr['prtfcorr'][x] = 1 - ( ( pd.np.mean(tradescorr['corrs'][x]) + 1 ) / 2 )
    return tradescorr

def _fxrates(acc_ccy):
    params = { 'instruments': "AUD_USD,EUR_USD,GBP_USD,NZD_USD,XAG_USD"}
    request = api_pricing.PricingInfo(accountID=accountID, params=params)
    rprices = pd.DataFrame(oanda_api.request(request)['prices'])
    fx1 = pd.DataFrame()
    fx1['ccy'] = rprices['instrument']
    fx1['ccy'] = fx1['ccy'].str.split('_', expand= True)[0]
    fx1['rate'] = round(1/((rprices['closeoutBid'].astype(float)+rprices['closeoutAsk'].astype(float))/2), 5)
    usd = pd.DataFrame({'ccy':['USD'], 'rate':[1]})
    fx1 = fx1.append(usd)
    fx1 = fx1.set_index('ccy')
    params = { 'instruments': "USD_CAD,USD_CHF,USD_CNH,USD_CZK,USD_DKK,USD_HKD,USD_HUF,USD_INR,USD_JPY,USD_MXN,USD_NOK,USD_PLN,USD_SAR,USD_SEK,USD_SGD,USD_THB,USD_TRY,USD_ZAR"}
    request = api_pricing.PricingInfo(accountID=accountID, params=params)
    rprices = pd.DataFrame(oanda_api.request(request)['prices'])
    fx2 = pd.DataFrame()
    fx2['ccy'] = rprices['instrument']
    fx2['ccy'] = fx2['ccy'].str.split('_', expand= True)[1]
    fx2['rate'] = round((rprices['closeoutAsk'].astype(float)+rprices['closeoutBid'].astype(float))/2, 5)
    fx2 = fx2.set_index('ccy')
    fx = fx1.append(fx2)
    ccy = fx['rate'][acc_ccy]
    fx['rate'] = fx['rate']/ccy
    return fx

def _optimalsizes(ntrades,risk,balance,conf,tradescorr,betas,fxrates):
    if ntrades > 1:
        riskexpected = risk*conf
        optimalsizes = pd.DataFrame()
        optimalsizes['symbol'] = tradescorr.index
        optimalsizes = optimalsizes.set_index('symbol')
        optimalsizes['price'] = _mids(optimalsizes.index)
        optimalsizes['dir'] = tradescorr['dir']
        optimalsizes['size'] = betas[10:15].mean()/100
        optimalsizes['size'] = riskexpected / optimalsizes['size'] * tradescorr['prtfcorr']
        optimalsizes['size'] = optimalsizes['size'] * balance / optimalsizes['price'] / len(optimalsizes)
        for sym in optimalsizes.index:
            ccy = sym.split('_')[1]
            optimalsizes['size'][sym] = optimalsizes['size'][sym] * fxrates['rate'][ccy]
        optimalsizes['size'] = pd.np.where((optimalsizes['dir'])>0,optimalsizes['size'],-optimalsizes['size'])
        optimalsizes['size'] = optimalsizes['size'].astype(int)
        return optimalsizes

def _currentsizes(trades):
    currentsizes = pd.DataFrame()
    currentsizes['symbol'] = trades['symbol']
    currentsizes['price'] = trades['price'].astype(float)
    currentsizes['dir'] = 0
    currentsizes['size'] = trades['size']
    currentsizes['vwap'] = currentsizes['price'] * currentsizes['size']
    currentsizes = currentsizes.groupby(['symbol']).sum()
    currentsizes['price'] = currentsizes['vwap']/currentsizes['size']
    currentsizes['dir'] = pd.np.where((currentsizes['size'])>0,1,-1)
    currentsizes = currentsizes.drop(['vwap'],axis=1)
    return currentsizes

def _residualsizes(optimalsizes,currentsizes):
    if not optimalsizes.empty:
        residualsizes = pd.DataFrame()
        residualsizes['price'] = optimalsizes['price']
        residualsizes['dir'] = optimalsizes['dir']
        residualsizes['size'] = optimalsizes['size']*optimalsizes['dir']
        residualsizes['size'] = residualsizes['size'] - currentsizes['size']*currentsizes['dir']
        residualsizes['size'] = residualsizes['size'].astype(int)
        return residualsizes

def _execlimits(residualsizes):
    if not residualsizes.empty:
        for sym in residualsizes.index:
            if residualsizes['size'][sym] != 0:
                size = int(residualsizes['size'][sym])
                print("\n")
                print("executing LIMIT "+sym+" "+str(size))
                executed = False
                while not executed:
                    try: 
                        quotes = _quotes(residualsizes.index)
                        if residualsizes['size'][sym] > 0:
                            price = quotes['bid'][sym]
                        elif residualsizes['size'][sym] < 0:
                            price = quotes['ask'][sym]
                        else:
                            break
                        data =  {
                                    "order": {
                                        "price": price,
                                        "timeInForce": "GTC",
                                        "instrument": sym,
                                        "units": size,
                                        "type": "LIMIT",
                                        "positionFill": "DEFAULT"
                                    }
                                }
                        request = api_orders.OrderCreate(accountID, data=data)
                        print(oanda_api.request(request))
                        executed = True
                    except:
                        pass
    
def _execmarkets(residualsizes):
    if not residualsizes.empty:
        for sym in residualsizes.index:
            if residualsizes['size'][sym] != 0:
                size = int(residualsizes['size'][sym])
                print("\n")
                print("executing MARKET "+sym+" "+str(size))
                executed = False
                while not executed:
                    try: 
                        data =  {
                                    "order": {
                                        "instrument": sym,
                                        "units": size,
                                        "type": "MARKET",
                                        "positionFill": "DEFAULT"
                                    }
                                }
                        request = api_orders.OrderCreate(accountID, data=data)
                        print(oanda_api.request(request))
                        executed = True
                    except:
                        pass

### ___Main___ ###

prnt = True

def main():
    trades = _trades(accountID)
    ntrades = _ntrades(trades)
    syms = _syms(trades)
    if ntrades > 0:
        betas = _betas(table)
        setTPSL = _setTPSL(betas,trades)
        quotes = _quotes(syms)
        stats = _stats(accountID)
        conf = _conf(stats)
        corrs = _corrs(tf)
        tradescorr = _tradescorr(trades,corrs)
        fxrates = _fxrates(currency)
        optimalsizes = _optimalsizes(ntrades,risk,balance,conf,tradescorr,betas,fxrates)
        currentsizes = _currentsizes(trades)
        residualsizes = _residualsizes(optimalsizes,currentsizes)        
        #_execlimits(residualsizes)
        _execmarkets(residualsizes)
        if prnt:
            print('\n',trades)
            #print('\n',betas)
            print('\n',setTPSL)
            print('\n',quotes)
            #print('\n',stats)
            print('\n',conf)
            #print('\n',corrs)
            print('\n',tradescorr)
            print('\n',optimalsizes)
            print('\n',currentsizes)
            print('\n',residualsizes)
    else:
        print('\n','FLAT')
   

if __name__ == "__main__":
    while True:      
        main()
        time.sleep(5)




