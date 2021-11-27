
import azure.functions as func
import requests
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta, TH
import mimetypes
import logging
import matplotlib.pyplot as plt
import os
import tempfile
from azure.storage.blob import BlockBlobService,ContentSettings
from . import optionlibraries
from datetime import date
import jinja2

account_name = 'optiontablestorage'
account_key = 'eURoD2XMmUgt7zuY9jX9IPXs9WhO5xCkU2du8gcibAdAeGFTmQUKVbyKy+MIN3UQxAu/AV6SMkzmVpimibI2EQ=='
mycontainer="opt-table"

nifty_lotsize=50

def main(req: func.HttpRequest,  context: func.Context) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    block_blob_service = BlockBlobService(
    account_name=account_name,
    account_key=account_key
    )

    str_next_thursday_expiry,_=optionlibraries.nextThu_and_lastThu_expiry_date()
    pcr,timestamp,niftySpot,df_call_near_expiry,df_put_near_expiry=optionlibraries.optionChain(str_next_thursday_expiry)
    df_call_near_expiry=df_call_near_expiry.drop(['identifier','pChange','underlying','bidprice','askQty','askPrice','totalSellQuantity','bidQty','change','totalBuyQuantity'], axis = 1)
    df_call_near_expiry['changeinOpenInterest']=nifty_lotsize * pd.to_numeric(df_call_near_expiry['changeinOpenInterest'])
    df_call_near_expiry['openInterest'] = nifty_lotsize * pd.to_numeric(df_call_near_expiry['openInterest'])
    df_call_near_expiry=df_call_near_expiry.nlargest(5, ['openInterest'])
    df_put_near_expiry=df_put_near_expiry.drop(['identifier','pChange','underlying','bidprice','askQty','askPrice','totalSellQuantity','bidQty','change','totalBuyQuantity'], axis = 1)
    df_put_near_expiry['openInterest'] = nifty_lotsize * pd.to_numeric(df_put_near_expiry['openInterest'])
    df_put_near_expiry['changeinOpenInterest']=nifty_lotsize * pd.to_numeric(df_put_near_expiry['changeinOpenInterest'])
    df_put_near_expiry=df_put_near_expiry.nlargest(5, ['openInterest'])

    #market Status
    marketStatus,marketStatusValue =optionlibraries.marketStatus()
    #calculate Option Greeks for Call
    if not (date.today().strftime("%d-%b-%Y")==df_call_near_expiry['expiryDate'].iloc[0]):
        #calculate Option Greeks for Call only when expiry date is not equal to todays date
        df_call_near_expiry=optionlibraries.calculateOptionGreeks(df_call_near_expiry,'Call',str_next_thursday_expiry)

        #Calculate Option Greeks for Put
        df_put_near_expiry=optionlibraries.calculateOptionGreeks(df_put_near_expiry,'Put',str_next_thursday_expiry)

    ## Update the columns for plotting graphs based on OI, Change in OI and Volume
    df_call_for_graph=df_call_near_expiry.drop(['expiryDate','pchangeinOpenInterest','impliedVolatility','lastPrice'], axis = 1)
    df_put_for_graph=df_put_near_expiry.drop(['expiryDate','pchangeinOpenInterest','impliedVolatility','lastPrice'], axis = 1)
    df_call_near_expiry=df_call_near_expiry.drop(['underlyingValue','expiryDate'], axis = 1)
    df_put_near_expiry=df_put_near_expiry.drop(['underlyingValue','expiryDate'], axis = 1)

    df_put_for_graph=df_put_for_graph.sort_index(axis = 0) 
    df_call_for_graph=df_call_for_graph.sort_index(axis = 0) 

    ax = df_call_for_graph.plot(x="strikePrice", y=["openInterest","changeinOpenInterest","totalTradedVolume"], kind="bar")
    ax.get_yaxis().get_major_formatter().set_scientific(False)
    ax.set_title('Top 5 - Call Option OI, Volume and Changes in OI', fontsize=10)
    for label in ax.xaxis.get_ticklabels():
        label.set_rotation(45)    
    for p in ax.patches:
        ax.annotate(str(round(p.get_height(),2)), (p.get_x() * 1.005, p.get_height() * 1.005),color='blue')
    plt.tight_layout()
    temp_path = tempfile.gettempdir()
    file_path = os.path.join(temp_path, 'callchartOI.png')
    
    plt.savefig(file_path, format = 'png')
    
    # saving file to Blob Container
    block_blob_service.create_blob_from_path(
    mycontainer,
    "callchartOI.png",
    file_path,
    content_settings=ContentSettings(content_type='image/png')
    )

    ax = df_put_for_graph.plot(x="strikePrice", y=["openInterest","changeinOpenInterest","totalTradedVolume"], kind="bar")
    ax.get_yaxis().get_major_formatter().set_scientific(False)
    ax.set_title('Top 5 - Put Option OI, Volume and Changes in OI', fontsize=10)
    for label in ax.xaxis.get_ticklabels():
        label.set_rotation(45)
    for p in ax.patches:
        ax.annotate(str(round(p.get_height(),2)), (p.get_x() * 1.005, p.get_height() * 1.005),color='blue')
    plt.tight_layout()

    file_path = os.path.join(temp_path, 'putchartOI.png')
    plt.savefig(file_path, format = 'png')
    block_blob_service.create_blob_from_path(
    mycontainer,
    "putchartOI.png",
    file_path,
    content_settings=ContentSettings(content_type='image/png')
    )

    df_global=optionlibraries.global_indices()
    column_names = ["Current Market parameters","Value"]
    df_mark_par = pd.DataFrame(columns = column_names)
    indVix=optionlibraries.indiavix()
    fiidata=optionlibraries.fiidata()
    df_mark_par.loc[len(df_mark_par.index)] = ["India VIX",indVix] 
    df_mark_par.loc[len(df_mark_par.index)] = ["Put Call Ratio (PCR)",pcr] 
    df_mark_par.loc[len(df_mark_par.index)] = ["FII Index Options (previous day)",fiidata] 
    df_mark_par= df_mark_par.style.hide_index().applymap(optionlibraries.color_negative_red, subset=['Value']).render()

    if "-" in marketStatusValue:
        colorvalue = 'red'
    else:
        colorvalue = 'green'

    htmltemplate= "<head> <title>Dynamic Option Strategy</title></head>" + "\n" +"<h2> Nifty Spot : <b style=\"color:" + colorvalue+ "\">" + str(niftySpot) + "\t" +"<i>" + str(marketStatusValue) + "</i> </b>" + "| Market Status : " + str(marketStatus) + " | Last Updated Time : " + timestamp + "</h2> <h3>" + df_global + "</h3><h3>" + df_mark_par + "</h3><style> h3 { text-align: right;} </style><h3>  <a href=\"http://20.102.61.30/\">Option Strategy</a> </h3>"
    tmpvarcall="<h4> Top 5 Strike price of Call Option based on Open Interest for Expiry Date = "+str_next_thursday_expiry + " </h4>"
    tmpvarput="<h4> Top 5 Strike price of Put  Option based on Open Interest for Expiry Date = "+str_next_thursday_expiry + " </h4>"
    df_put_near_expiry=df_put_near_expiry.rename({'strikePrice': 'Strike Price', 'expiryDate': 'Option Expiry Date','openInterest':'Open Interest (OI)','changeinOpenInterest':'Change in OI','pchangeinOpenInterest':'% Change in OI','totalTradedVolume':'Traded Volume','impliedVolatility':'IV','lastPrice':'Price'}, axis=1)
    df_call_near_expiry=df_call_near_expiry.rename({'strikePrice': 'Strike Price', 'expiryDate': 'Option Expiry Date','openInterest':'Open Interest (OI)','changeinOpenInterest':'Change in OI','pchangeinOpenInterest':'% Change in OI','totalTradedVolume':'Traded Volume','impliedVolatility':'IV','lastPrice':'Price'}, axis=1)
    df_call_near_expiry.set_index('Strike Price', inplace=True)
    df_put_near_expiry.set_index('Strike Price', inplace=True)


    df_call_near_expiry=df_call_near_expiry.reset_index(drop=False)
    iddx1 = df_call_near_expiry['Strike Price'].sub(niftySpot).abs().idxmin()
    idx1 = pd.IndexSlice
    slice1_ = idx1[idx1[iddx1]]
    call_render=df_call_near_expiry.style.hide_index().format(formatter={('Price'): "{:.2f}",('Delta(Δ)'): "{:.3f}",('Gamma(γ)'): "{:.3f}",('Theta(Θ)'): "{:.3f}",('% Change in OI'): "{:.2f}",('IV'): "{:.2f}"}).set_properties(**{'background-color': '#ffffb3'},**{'width': '100'}, subset=slice1_).render()

    df_put_near_expiry=df_put_near_expiry.reset_index(drop=False)
    iddx2 = df_put_near_expiry['Strike Price'].sub(niftySpot).abs().idxmin()
    idx2 = pd.IndexSlice
    slice2_ = idx2[idx2[iddx2]]
    put_render=df_put_near_expiry.style.hide_index().format(formatter={('Price'): "{:.2f}",('Delta(Δ)'): "{:.3f}",('Gamma(γ)'): "{:.3f}",('Theta(Θ)'): "{:.3f}",('% Change in OI'): "{:.2f}",('IV'): "{:.2f}"}).set_properties(**{'background-color': '#ffffb3'},**{'width': '100px'}, subset=slice2_).render() 

     
    filename = os.path.join(temp_path, 'index.html')
    tobePrinted= htmltemplate + "<style> h4 {text-align:center;} </style> <h4> Option Chain data for " + str_next_thursday_expiry + " </h4>"+ "\n" +"\n" + tmpvarcall + "\n" + "\n" + call_render   + "<h5>" + "<img src='https://optiontablestorage.blob.core.windows.net/opt-table/callchartOI.png'>"+ "</h4>" + "\n===========================================================" + "\n\n" + "\n" +"\n" + tmpvarput + "\n" + "\n" + put_render + "\n" + "<h4>" + "<img src='https://optiontablestorage.blob.core.windows.net/opt-table/putchartOI.png'> =========================================================== </h4>"
   
    
    text_file = open(filename, "w", encoding='utf8')
    text_file.write(tobePrinted)
    text_file.close()

    #filename = f"/tmp/index.html"
    with open(filename, 'rb') as f:
        mimetype = mimetypes.guess_type(filename)
        return func.HttpResponse(f.read(), mimetype=mimetype[0])