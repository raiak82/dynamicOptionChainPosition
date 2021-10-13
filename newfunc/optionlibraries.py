import requests
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta, TH
import quantsbin.derivativepricing as qbdp
from quantsbin.derivativepricing.namesnmapper import VanillaOptionType, ExpiryType, UdlType, OBJECT_MODEL, DerivativeType
from datetime import date
from lxml import html
from lxml.etree import tostring
from bs4 import BeautifulSoup

DIV_YIELD= 0.0344 # RBI Dividend yield
def marketStatus():
    url="https://www.nseindia.com/api/marketStatus"
    urlheader = {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
      "authority": "www.nseindia.com",
      "scheme":"https"
    }
    res = requests.get(url, headers=urlheader).json()
    mstatus=res['marketState'][0]['marketStatus']

    url="https://www.nseindia.com"
    urlheader = {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
      "authority": "www.nseindia.com",
      "scheme":"https"
    }
    res = requests.get(url, headers=urlheader)
    tree = html.fromstring(res.content)  
    marketChange = tree.xpath('//*[@id="marketStat0"]/div[2]/span/text()')
    return(mstatus,marketChange[0])

def optionChain (expirydate):

    urlheader = {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
      "authority": "www.nseindia.com",
      "scheme":"https"
    }
        
    url="https://www.nseindia.com/api/option-chain-indices?"
    params="symbol=NIFTY"
    
    url_encoded=url + params
    
    req = requests.get(url_encoded, headers=urlheader).json()
    call = []
    put = []
    strikePrices=[]
    timestamp=req['records']['timestamp']
    niftySpot=req['records']['underlyingValue']
    for eachstrike in req['records']['strikePrices']:
        strikePrices.append(eachstrike)
    for each in strikePrices:
        for rec in req['records']['data']:
            if rec['expiryDate']==expirydate and rec['strikePrice']==each:
                temp_call={}
                temp_put={}
                for k,v in rec['CE'].items():
                     temp_call[k] = v
                call.append(temp_call)
                for k,v in rec['PE'].items():
                    temp_put[k]=v
                put.append(temp_put)
                
                
    df_call = pd.DataFrame(call)
    df_put = pd.DataFrame(put)
        

    totCallOI=req['filtered']['CE']['totOI']
    totputOI=req['filtered']['PE']['totOI']
    pcr="{:.2f}".format(totputOI/totCallOI)
        

    return(pcr,timestamp,niftySpot,df_call,df_put)



def nextThu_and_lastThu_expiry_date ():

    todayte = datetime.today()
    
    cmon = todayte.month
    if_month_next=(todayte + relativedelta(weekday=TH(1))).month
    next_thursday_expiry=todayte + relativedelta(weekday=TH(1))
   
    if (if_month_next!=cmon):
        month_last_thu_expiry= todayte + relativedelta(weekday=TH(5))
        if (month_last_thu_expiry.month!=if_month_next):
            month_last_thu_expiry= todayte + relativedelta(weekday=TH(4))
    else:
        for i in range(1, 7):
            t = todayte + relativedelta(weekday=TH(i))
            if t.month != cmon:
                # since t is exceeded we need last one  which we can get by subtracting -2 since it is already a Thursday.
                t = t + relativedelta(weekday=TH(-2))
                month_last_thu_expiry=t
                break
    str_month_last_thu_expiry=str(month_last_thu_expiry.strftime("%d")) + "-" + month_last_thu_expiry.strftime("%b").title() + "-" +month_last_thu_expiry.strftime("%Y")
    str_next_thursday_expiry=str(next_thursday_expiry.strftime("%d")) + "-" + next_thursday_expiry.strftime("%b").title() + "-" + next_thursday_expiry.strftime("%Y")
    return (str_next_thursday_expiry,str_month_last_thu_expiry)


def calculateOptionGreeks (df,option_type,expiryDate):
    df['Delta(\u0394)']=pd.Series(dtype='float64')
    df['Gamma(\u03B3)']=pd.Series(dtype='float64')
    df['Theta(\u0398)']=pd.Series(dtype='float64')
    pricing_date=date.today().strftime("%Y%m%d")
    df['expiryDate']= pd.to_datetime(df['expiryDate'])
    for index,val in df.iterrows():
        custdate=val['expiryDate'].strftime("%Y%m%d")
        
        market1_parameters = {'spot0': float(val['underlyingValue'])
                     , 'pricing_date':pricing_date
                     , 'volatility':0.01*float(val['impliedVolatility'])
                     , 'rf_rate':DIV_YIELD
                     , 'yield_div':0.0}

        equity_p1 = qbdp.EqOption(option_type=option_type, strike=float(val['strikePrice']), expiry_date=custdate, expiry_type='European')

        eq1_BSM_market1 = equity_p1.engine(model="BSM", **market1_parameters)
        
        df.at[index,'Delta(\u0394)']=float(eq1_BSM_market1.risk_parameters()['delta'])
        df.at[index,'Gamma(\u03B3)']=float(eq1_BSM_market1.risk_parameters()['gamma'])
        df.at[index,'Theta(\u0398)']=float(eq1_BSM_market1.risk_parameters()['theta'])
    return df


def dowfuture():
    url="https://www.investing.com/indices/us-30-futures"
    urlheader = {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
      "authority": "www.investing.com",
      "scheme":"https"
    }
    res = requests.get(url, headers=urlheader)
    tree = html.fromstring(res.content)  
  
    # Get element using XPath
    dow_fut = tree.xpath('//*[@id="__next"]/div/div/div[2]/main/div/div[1]/div[2]/div[1]/span/text()')
    dow_fut_change=tree.xpath('///*[@id="__next"]/div/div/div[2]/main/div/div[1]/div[2]/div[1]/div[2]/span[1]/text()')
    dow_fut_perc_change=tree.xpath('//*[@id="__next"]/div/div/div[2]/main/div/div[1]/div[2]/div[1]/div[2]/span[2]/text()')
    return(dow_fut[0],dow_fut_change[0],dow_fut_perc_change[1])

def nikkeifuture():
    url="https://www.investing.com/indices/japan-225-futures"
    urlheader = {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
      "authority": "www.investing.com",
      "scheme":"https"
    }
    res = requests.get(url, headers=urlheader)
    tree = html.fromstring(res.content)  
  
    # Get element using XPath
    nik_fut = tree.xpath('//*[@id="__next"]/div/div/div[2]/main/div/div[1]/div[2]/div[1]/span/text()')
    nik_fut_change=tree.xpath('///*[@id="__next"]/div/div/div[2]/main/div/div[1]/div[2]/div[1]/div[2]/span[1]/text()')
    nik_fut_perc_change=tree.xpath('//*[@id="__next"]/div/div/div[2]/main/div/div[1]/div[2]/div[1]/div[2]/span[2]/text()')
    return(nik_fut[0],nik_fut_change[0],nik_fut_perc_change[1])

def ftseFuture():
    url="https://www.investing.com/indices/uk-100-futures"
    urlheader = {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
      "authority": "www.investing.com",
      "scheme":"https"
    }
    res = requests.get(url, headers=urlheader)
    tree = html.fromstring(res.content)  
  
    # Get element using XPath
    ftse_fut = tree.xpath('//*[@id="__next"]/div/div/div[2]/main/div/div[1]/div[2]/div[1]/span/text()')
    ftse_fut_change=tree.xpath('///*[@id="__next"]/div/div/div[2]/main/div/div[1]/div[2]/div[1]/div[2]/span[1]/text()')
    ftse_fut_perc_change=tree.xpath('//*[@id="__next"]/div/div/div[2]/main/div/div[1]/div[2]/div[1]/div[2]/span[2]/text()')
    return(ftse_fut[0],ftse_fut_change[0],ftse_fut_perc_change[1])


def indiavix():
    url="https://www1.nseindia.com/live_market/dynaContent/live_watch/VixDetails.json"
    urlheader = {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
      "Host": "www1.nseindia.com"
    }
    res = requests.get(url,headers=urlheader).json()
    viX_perc_change=res['currentVixSnapShot'][0]['PERC_CHANGE']
    vix_current=res['currentVixSnapShot'][0]['CURRENT_PRICE']
    vix=vix_current + " (" + viX_perc_change + "% )"

    return(vix)

def global_indices():      
    
    column_names = ["Global Indices","Current Value"]
    df_global = pd.DataFrame(columns = column_names)
     
    curDow,_,perDowChange=dowfuture()
    curDow=str(curDow)
    perDowChange=str(perDowChange)
    
    curDow= curDow + "  (" + perDowChange + ")"
    
    curFtse,_,perFtseChange=ftseFuture()
    curFtse=str(curFtse)
    perFtseChange=str(perFtseChange)
    
    curFtse=curFtse + "  (" + perFtseChange + ")"
    
    curNik,_,perNikChange=nikkeifuture()
    curNik=str(curNik)
    perNikChange=str(perNikChange)
    
    curNik=curNik + "  (" + perNikChange + ")"
    
    
    
    df_global.loc[len(df_global.index)] = ["Dow Futures (US)",curDow] 
    df_global.loc[len(df_global.index)] = ["Nikkei Futures (Japan)",curNik] 
    df_global.loc[len(df_global.index)] = ["FTSE Futures (London)",curFtse] 
    df_global_render= df_global.style.hide_index().applymap(color_negative_red, subset=['Current Value']).render()
    
    return(df_global_render)


def color_negative_red(value):
  """
  Colors elements in a dateframe
  green if positive and red if
  negative. Does not color NaN
  values.
  """

  if "-" in value:
    color = 'red'
  elif "+" in value:
    color = 'green'
  else:
    color = 'black'

  return 'color: %s' % color


def fiidata():
    
    url = 'https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx'
    
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'lxml')
    
    # get all tables
    tables = soup.find_all('table')
    
    rows = tables[1].find_all('tr')
    for row in rows:
        columns = row.find_all('td')
        row_val=([column.text.strip() for column in columns])
        if "Index Options" in row_val:
            IndexBuy=row_val[2]
            IndexSell=row_val[4]
            FIIData=float(IndexBuy)-float(IndexSell)
    return(str(int(FIIData)) + " Cr") 