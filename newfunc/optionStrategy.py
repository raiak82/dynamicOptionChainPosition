from azure.storage.blob import BlockBlobService,ContentSettings
from . import opstrat as op
import datetime
import requests
import pandas as pd
import os
import tempfile
from azure.data.tables import TableClient
from azure.data.tables import UpdateMode
from . import optionlibraries
nifty_lotsize=50

access_key = "testoptable"
endpoint_suffix = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
account_name = "testop"
endpoint = "{}.table.{}".format(account_name, endpoint_suffix)
table_name="strat"
connection_string = "DefaultEndpointsProtocol=https;AccountName=testoptable;AccountKey=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX;EndpointSuffix=core.windows.net"
table=TableClient.from_connection_string(connection_string, table_name=table_name)


account_name = 'testoptable'
account_key = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
mycontainer="testop"

block_blob_service = BlockBlobService(
account_name=account_name,
account_key=account_key
)
def optionStrategy():   
    entities = list(table.list_entities())
    entity=entities[0]
    today = datetime.date.today()
    todaydt_global= str(today.strftime("%d-%m-%Y"))
    today = datetime.date.today()
    todaydt= str(today.strftime("%A %d, %Y"))
    if todaydt_global != entity['currday']:
        
        htmltemplate = "<h4> Option Strategy </h4>"
    
        now = datetime.datetime.now()
        curday=now.strftime("%A")
        str_next_thursday_expiry,_=optionlibraries.nextThu_and_lastThu_expiry_date()
        _,_,_,df_call,df_put=optionlibraries.optionChain(str_next_thursday_expiry)
        df_call=df_call.drop(['identifier','pChange','underlying','bidprice','askQty','askPrice','totalSellQuantity','bidQty','change','totalBuyQuantity'], axis = 1)
        df_call['changeinOpenInterest']=nifty_lotsize * pd.to_numeric(df_call['changeinOpenInterest'])
        df_call['openInterest'] = nifty_lotsize * pd.to_numeric(df_call['openInterest'])
        df_put=df_put.drop(['identifier','pChange','underlying','bidprice','askQty','askPrice','totalSellQuantity','bidQty','change','totalBuyQuantity'], axis = 1)
        df_put['openInterest'] = nifty_lotsize * pd.to_numeric(df_put['openInterest'])
        df_put['changeinOpenInterest']=nifty_lotsize * pd.to_numeric(df_put['changeinOpenInterest'])
        #df_put = pd.read_csv("https://testoptable.blob.core.windows.net/testop/df_put_near_expiry.csv")
        #df_call = pd.read_csv("https://testoptable.blob.core.windows.net/testop/df_call_near_expiry.csv")
        nfSpot=df_call['underlyingValue'][0]
        idx_call = df_call.strikePrice.sub(nfSpot).abs().idxmin()
        idx_put = df_put.strikePrice.sub(nfSpot).abs().idxmin()
        call_nearestStrike=df_call.loc[idx_call]['strikePrice']
        put_nearestStrike=df_put.loc[idx_put]['strikePrice']
        call_short=call_nearestStrike
        put_short=put_nearestStrike
        if curday == "Friday":
            htmltemplate= htmltemplate + "<h4>Plain Vanilla Call short and Put short Option for decay over the weekend </h4>"
            if call_nearestStrike%100 == 0:
                call_short=call_short+100
                put_short=put_short-100
            else:
                call_short=call_short+50
                put_short=put_short-50
            df_tmp=df_call.copy()
            df_tmp.set_index('strikePrice', inplace=True)
            op1={'op_type': 'c', 'strike': call_nearestStrike+100 , 'tr_type': 's', 'op_pr': df_tmp.loc[call_nearestStrike+100]['lastPrice']}
            callOptionString="Nifty Index Expiry "+ str(df_tmp.loc[call_nearestStrike+100]['expiryDate']) + " | Sell 1 lot CE-Strike " + str(call_nearestStrike+100) + " @" + str(df_tmp.loc[call_nearestStrike+100]['lastPrice'])
            del(df_tmp)
            df_tmp=df_put.copy()
            df_tmp.set_index('strikePrice', inplace=True)
            putOptionString="Nifty Index Expiry "+ str(df_tmp.loc[put_nearestStrike-100]['expiryDate']) + " | Sell 1 lot PE-Strike " + str(put_nearestStrike-100) + " @" + str(df_tmp.loc[put_nearestStrike-100]['lastPrice'])       
            op2={'op_type': 'p', 'strike': put_nearestStrike-100, 'tr_type': 's', 'op_pr': df_tmp.loc[put_nearestStrike-100]['lastPrice']}
            del(df_tmp)
            op_list=[op1, op2]
            htmltemplate= htmltemplate + "<h4> Sell 1 lot of Nifty Call at Strike Price " + str(call_nearestStrike+100) + " and 1 lot of Nifty Put at Strike Price " + str(put_nearestStrike-100) + " only for weekend and exit early next day when Profit is atleast >1000 rupees </h4>"
            temp_path = tempfile.gettempdir()
            file_path = os.path.join(temp_path, 'plot2.png')
            op.multi_plotter(spot=nfSpot,spot_range=2, op_list=op_list,save=True,file=file_path)
            block_blob_service.create_blob_from_path(
            mycontainer,
            "plot2.png",
            file_path,
            content_settings=ContentSettings(content_type='image/png')
            )
            htmltemplate = htmltemplate + "<h5> " + callOptionString + "<br>" + putOptionString + "</h5>"
            
            htmltemplate = htmltemplate + "<h5> <img src='https://testoptable.blob.core.windows.net/testop/plot2.png' /> </h5>"
            
            htmltemplate= htmltemplate + "<h6>========================================================================================================================================================================================================</h6>"
            
            htmltemplate= htmltemplate + "<h3>Covered Call Option for period of Monday and Tuesday- Exit when profit is more than 1.5K </h3>"
            htmltemplate= htmltemplate + "<h4> Buy 1 lot of Nifty Call at Strike Price " + str(call_nearestStrike) + " and sell 1 lot of Nifty Call at Strike Price " + str(call_nearestStrike+100) + " and sell 1 lot of Nifty Call at Strike Price " + str(call_nearestStrike+200) +" </h4>"
            
            df_tmp=df_call.copy()
            df_tmp.set_index('strikePrice', inplace=True)
            op1={'op_type': 'c', 'strike': call_nearestStrike , 'tr_type': 'b', 'op_pr': df_tmp.loc[call_nearestStrike]['lastPrice']}
            op2={'op_type': 'c', 'strike': call_nearestStrike+100 , 'tr_type': 's', 'op_pr': df_tmp.loc[call_nearestStrike+100]['lastPrice']}
            op3={'op_type': 'c', 'strike': call_nearestStrike+200 , 'tr_type': 's', 'op_pr': df_tmp.loc[call_nearestStrike+200]['lastPrice']}
            callOptionString1="Nifty Index Expiry "+ str(df_tmp.loc[call_nearestStrike]['expiryDate']) + " | Buy 1 lot CE-Strike " + str(call_nearestStrike) + " @" + str(df_tmp.loc[call_nearestStrike]['lastPrice'])
            callOptionString2="Nifty Index Expiry "+ str(df_tmp.loc[call_nearestStrike+100]['expiryDate']) + " | Buy 1 lot CE-Strike " + str(call_nearestStrike+100) + " @" + str(df_tmp.loc[call_nearestStrike+100]['lastPrice'])
            callOptionString3="Nifty Index Expiry "+ str(df_tmp.loc[call_nearestStrike+200]['expiryDate']) + " | Buy 1 lot CE-Strike " + str(call_nearestStrike+200) + " @" + str(df_tmp.loc[call_nearestStrike+200]['lastPrice'])
            del(df_tmp)
            op_list=[op1, op2, op3]
            temp_path = tempfile.gettempdir()
            file_path = os.path.join(temp_path, 'plot3.png')
            op.multi_plotter(spot=nfSpot,spot_range=2, op_list=op_list,save=True,file=file_path)
            block_blob_service.create_blob_from_path(
            mycontainer,
            "plot3.png",
            file_path,
            content_settings=ContentSettings(content_type='image/png')
            )
            htmltemplate = htmltemplate + "<h5> " + callOptionString1 + "<br>" + callOptionString2 +"<br>" + callOptionString3 + "</h5>"
            
            htmltemplate = htmltemplate + "<h5> <img src='https://testoptable.blob.core.windows.net/testop/plot3.png' /> </h5>"
            
            htmltemplate= htmltemplate + "<h6>========================================================================================================================================================================================================</h6>"
            
            htmltemplate= htmltemplate + "<h3>Covered Put Option for period of Monday and Tuesday- Exit when profit is more than 1.5K </h3>"
            htmltemplate= htmltemplate + "<h4> Buy 1 lot of Nifty Put at Strike Price " + str(put_nearestStrike) + " and sell 1 lot of Nifty Put at Strike Price " + str(put_nearestStrike-100) + " and sell 1 lot of Nifty Put at Strike Price " + str(put_nearestStrike-200) +" </h4>"
            
            df_tmp=df_put.copy()
            df_tmp.set_index('strikePrice', inplace=True)
            op1={'op_type': 'p', 'strike': put_nearestStrike , 'tr_type': 'b', 'op_pr': df_tmp.loc[call_nearestStrike]['lastPrice']}
            op2={'op_type': 'p', 'strike': put_nearestStrike-100 , 'tr_type': 's', 'op_pr': df_tmp.loc[call_nearestStrike-100]['lastPrice']}
            op3={'op_type': 'p', 'strike': put_nearestStrike-200 , 'tr_type': 's', 'op_pr': df_tmp.loc[call_nearestStrike-200]['lastPrice']}
            putOptionString1="Nifty Index Expiry "+ str(df_tmp.loc[put_nearestStrike]['expiryDate']) + " | Buy 1 lot PE-Strike " + str(put_nearestStrike) + " @" + str(df_tmp.loc[put_nearestStrike]['lastPrice'])
            putOptionString2="Nifty Index Expiry "+ str(df_tmp.loc[put_nearestStrike-100]['expiryDate']) + " | Buy 1 lot PE-Strike " + str(put_nearestStrike-100) + " @" + str(df_tmp.loc[put_nearestStrike-100]['lastPrice'])
            putOptionString3="Nifty Index Expiry "+ str(df_tmp.loc[put_nearestStrike-200]['expiryDate']) + " | Buy 1 lot PE-Strike " + str(put_nearestStrike-200) + " @" + str(df_tmp.loc[put_nearestStrike-200]['lastPrice'])
            del(df_tmp)
            op_list=[op1, op2, op3]
            temp_path = tempfile.gettempdir()
            file_path = os.path.join(temp_path, 'plot4.png')
            op.multi_plotter(spot=nfSpot,spot_range=3, op_list=op_list,save=True,file=file_path)
            block_blob_service.create_blob_from_path(
            mycontainer,
            "plot4.png",
            file_path,
            content_settings=ContentSettings(content_type='image/png')
            )
            htmltemplate = htmltemplate + "<h5> " + putOptionString1 + "<br>" + putOptionString2 +"<br>" + putOptionString3 + "</h5>"
            
            htmltemplate = htmltemplate + "<h5> <img src='https://testoptable.blob.core.windows.net/testop/plot4.png' /> </h5>"
            
            entity["testvale"] = htmltemplate
            entity["currday"] = todaydt_global
            table.update_entity(mode=UpdateMode.MERGE, entity=entity)
        
        elif curday == "Monday":
            htmltemplate= htmltemplate + "<h3>Partial hedged- Call Option when Nifty is trending positive, exit when option decay is more than 30% next day</h3>"
            df_tmp1=df_call.copy()
            df_tmp1.set_index('strikePrice', inplace=True)
            
            nfSpot=df_call['underlyingValue'][0]
            
            if call_nearestStrike <= nfSpot:
                call_nearestStrike=call_nearestStrike+50
            if put_nearestStrike >= nfSpot:
                put_nearestStrike=put_nearestStrike-50
    
                
            op1={'op_type': 'c', 'strike': call_nearestStrike , 'tr_type': 'b', 'op_pr': df_tmp1.loc[call_nearestStrike]['lastPrice']}
            op2={'op_type': 'c', 'strike': call_nearestStrike+100, 'tr_type': 's', 'op_pr': df_tmp1.loc[call_nearestStrike+100]['lastPrice'], 'contract':1}
            
            op_list=[op1, op2]
            htmltemplate= htmltemplate + "<h4>Buy 1 lot of Nifty Call at Strike Price " + str(call_nearestStrike) + " and sell 1 lot of Nifty Call at Strike Price " + str(call_nearestStrike+100) + " exit the position if profit is more than 1K or exit if trend is reversed </h4>"

            callOptionString1="Nifty Index Expiry "+ str(df_call['expiryDate'][0]) + "Buy 1 lot CE-Strike " + str(call_nearestStrike) + " @" + str(df_tmp1.loc[call_nearestStrike]['lastPrice'])
            callOptionString2="Nifty Index Expiry "+ str(df_call['expiryDate'][0]) + "Sell 1 lot CE-Strike " + str(call_nearestStrike+100) + " @" + str(df_tmp1.loc[call_nearestStrike+100]['lastPrice'])
            htmltemplate = htmltemplate + "<h4> " + callOptionString1 + callOptionString2 +"</h4>"
            op.multi_plotter(spot=nfSpot,spot_range=1, op_list=op_list, save=True,file="plot10.png")
            del(df_tmp1)
            file_path=os.getcwd() + "\\plot10.png"
            block_blob_service.create_blob_from_path(
            mycontainer,
            "plot10.png",
            file_path,
            content_settings=ContentSettings(content_type='image/png')
            )
            htmltemplate = htmltemplate + "<h5> <img src='https://testoptable.blob.core.windows.net/testop/plot10.png' /> </h5>"
            
            htmltemplate= htmltemplate + "<h3>Partial hedged- Put Option when Nifty is trending negative, exit when option decay is more than 30% next day</h3>"
            
            htmltemplate= htmltemplate + "<h4>Buy 1 lot of Nifty Put at Strike Price " + str(put_nearestStrike) + " and sell 1 lot of Nifty Put at Strike Price " + str(put_nearestStrike-100) + " exit the position if profit is more than 1K or exit if trend is reversed </h4>"
            df_tmp=df_put.copy()
            df_tmp.set_index('strikePrice', inplace=True)
            op1={'op_type': 'p', 'strike': put_nearestStrike , 'tr_type': 'b', 'op_pr': df_tmp.loc[put_nearestStrike]['lastPrice']}
            op2={'op_type': 'p', 'strike': put_nearestStrike-100 , 'tr_type': 's', 'op_pr': df_tmp.loc[put_nearestStrike-100]['lastPrice']}
            op_list=[op1, op2]
            putOptionString1="Nifty Index Expiry "+ str(df_put['expiryDate'][0]) + "Buy 1 lot PE-Strike " + str(put_nearestStrike) + " @" + str(df_tmp.loc[put_nearestStrike]['lastPrice'])
            putOptionString2="Nifty Index Expiry "+ str(df_put['expiryDate'][0]) + "Sell 1 lot PE-Strike " + str(put_nearestStrike-100) + " @" + str(df_tmp.loc[put_nearestStrike-100]['lastPrice'])
            htmltemplate = htmltemplate + "<h4> " + putOptionString1 + putOptionString2 +"</h4>"
            op.multi_plotter(spot=nfSpot,spot_range=1, op_list=op_list, save=True,file="plot11.png")
            del(df_tmp)            
            file_path=os.getcwd() + "\\plot11.png"
            block_blob_service.create_blob_from_path(
            mycontainer,
            "plot11.png",
            file_path,
            content_settings=ContentSettings(content_type='image/png')
            )
            
            htmltemplate = htmltemplate + "<h5> <img src='https://testoptable.blob.core.windows.net/testop/plot11.png' /> </h5>"
            entity["testvale"] = htmltemplate
            entity["currday"] = todaydt_global
            table.update_entity(mode=UpdateMode.MERGE, entity=entity)                    
            
        elif curday == "Tuesday":
            htmltemplate= htmltemplate + "<h3> Covered Call Option taken till expiry- For position taken on Tuesday </h3>"
            df_tmp_call=df_call['openInterest'].nlargest(2).to_numpy()
            df_tmp_put=df_put['openInterest'].nlargest(2).to_numpy()
            df_tmp1=df_call.copy()
            df_tmp1.set_index('strikePrice', inplace=True)
    
                
            op1={'op_type': 'c', 'strike': call_nearestStrike , 'tr_type': 'b', 'op_pr': df_tmp1.loc[call_nearestStrike]['lastPrice']}
            op2={'op_type': 'c', 'strike': call_nearestStrike+100, 'tr_type': 's', 'op_pr': df_tmp1.loc[call_nearestStrike+100]['lastPrice'], 'contract':2}
    
            op_list=[op1, op2]
            htmltemplate= htmltemplate + "<h4>Buy 1 lot of Nifty Call at Strike Price " + str(call_nearestStrike) + " and sell 2 lot of Nifty Call at Strike Price " + str(call_nearestStrike+100) + " hold the position till expiry or exit when profit is more than 1.5K </h4>"
            nfSpot=df_call['underlyingValue'][0]
            callOptionString1="Nifty Index Expiry "+ str(df_call['expiryDate'][0]) + "Buy 1 lot CE-Strike " + str(call_nearestStrike) + " @" + str(df_tmp1.loc[call_nearestStrike]['lastPrice'])
            callOptionString2="Nifty Index Expiry "+ str(df_call['expiryDate'][0]) + "Sell 2 lot CE-Strike " + str(call_nearestStrike+100) + " @" + str(df_tmp1.loc[call_nearestStrike+100]['lastPrice'])
            htmltemplate = htmltemplate + "<h4> " + callOptionString1 + callOptionString2 +"</h4>"
            op.multi_plotter(spot=nfSpot,spot_range=1, op_list=op_list, save=True,file="plot5.png")
            del(df_tmp1)
            file_path=os.getcwd() + "\\plot5.png"
            block_blob_service.create_blob_from_path(
            mycontainer,
            "plot5.png",
            file_path,
            content_settings=ContentSettings(content_type='image/png')
            )
            htmltemplate = htmltemplate + "<h5> <img src='https://testoptable.blob.core.windows.net/testop/plot5.png' /> </h5>"
            htmltemplate= htmltemplate + "<h4>Buy 1 lot of Nifty Put at Strike Price " + str(put_nearestStrike) + " and sell 2 lot of Nifty Put at Strike Price " + str(put_nearestStrike-100) + " hold the position till expiry or exit when profit is more than 1.5K </h4>"
            df_tmp=df_put.copy()
            df_tmp.set_index('strikePrice', inplace=True)
            op1={'op_type': 'p', 'strike': put_nearestStrike , 'tr_type': 'b', 'op_pr': df_tmp.loc[put_nearestStrike]['lastPrice']}
            op2={'op_type': 'p', 'strike': put_nearestStrike-100 , 'tr_type': 's', 'op_pr': df_tmp.loc[put_nearestStrike-100]['lastPrice'],'contract':2}
            op_list=[op1, op2]
            putOptionString1="Nifty Index Expiry "+ str(df_put['expiryDate'][0]) + "Buy 1 lot PE-Strike " + str(put_nearestStrike) + " @" + str(df_tmp.loc[put_nearestStrike]['lastPrice'])
            putOptionString2="Nifty Index Expiry "+ str(df_put['expiryDate'][0]) + "Sell 2 lot PE-Strike " + str(put_nearestStrike-100) + " @" + str(df_tmp.loc[put_nearestStrike-100]['lastPrice'])
            htmltemplate = htmltemplate + "<h4> " + putOptionString1 + putOptionString2 +"</h4>"
            op.multi_plotter(spot=nfSpot,spot_range=1, op_list=op_list, save=True,file="plot6.png")
            del(df_tmp)            
            file_path=os.getcwd() + "\\plot6.png"
            block_blob_service.create_blob_from_path(
            mycontainer,
            "plot6.png",
            file_path,
            content_settings=ContentSettings(content_type='image/png')
            )
            
            htmltemplate = htmltemplate + "<h5> <img src='https://testoptable.blob.core.windows.net/testop/plot6.png' /> </h5>"
            entity["testvale"] = htmltemplate
            entity["currday"] = todaydt_global
            table.update_entity(mode=UpdateMode.MERGE, entity=entity)

        elif curday == "Wednesday":
            htmltemplate= htmltemplate + "<h3> Plain Vanilla of Short Call and Short Put at far away Strike with highest OI </h3>"
            df_tmp1=df_call.copy()
            df_tmp1.set_index('strikePrice', inplace=True)
            df_tmp2=df_put.copy()
            df_tmp2.set_index('strikePrice', inplace=True)
            op1={'op_type': 'c', 'strike': call_nearestStrike+150 , 'tr_type': 's', 'op_pr': df_tmp1.loc[call_nearestStrike+100]['lastPrice']}
            op2={'op_type': 'p', 'strike': put_nearestStrike-150, 'tr_type': 's', 'op_pr': df_tmp2.loc[put_nearestStrike-100]['lastPrice']}
    
            op_list=[op1, op2]
            htmltemplate= htmltemplate + "<h4>Sell 1 lot of Nifty Call at Strike Price " + str(call_nearestStrike+150) + " and sell 1 lot of Nifty Put at Strike Price " + str(put_nearestStrike-150) + " hold the position till expiry to gain premium decay </h4>"
            nfSpot=df_call['underlyingValue'][0]
            callOptionString1="Nifty Index Expiry "+ str(df_call['expiryDate'][0]) + "Sell 1 lot CE-Strike " + str(call_nearestStrike+150) + " @" + str(df_tmp1.loc[call_nearestStrike+150]['lastPrice'])
            callOptionString2="Nifty Index Expiry "+ str(df_call['expiryDate'][0]) + "Sell 1 lot PE-Strike " + str(put_nearestStrike-150) + " @" + str(df_tmp2.loc[put_nearestStrike-150]['lastPrice'])
            htmltemplate = htmltemplate + "<h4> " + callOptionString1 + callOptionString2 +"</h4>"
            op.multi_plotter(spot=nfSpot,spot_range=2, op_list=op_list, save=True,file="plot7.png")

            file_path=os.getcwd() + "\\plot7.png"
            block_blob_service.create_blob_from_path(
            mycontainer,
            "plot7.png",
            file_path,
            content_settings=ContentSettings(content_type='image/png')
            )
            htmltemplate = htmltemplate + "<h5> <img src='https://testoptable.blob.core.windows.net/testop/plot7.png' /> </h5>"
            htmltemplate= htmltemplate + "<h4> Call Straddle -Buy 1 lot of Nifty Call at the money Strike Price " + str(call_nearestStrike) + " and sell 1 lot of Nifty Call at Strike Price " + str(call_nearestStrike+50) + " and sell another 1 lot of Nifty Call at Strike Price " + str(call_nearestStrike+150)+ " hold the position till expiry if Nifty trend is positive or exit if trend is negative. Risk is however minimal </h4>"
            op1={'op_type': 'c', 'strike': call_nearestStrike , 'tr_type': 'b', 'op_pr': df_tmp1.loc[call_nearestStrike]['lastPrice']}
            op2={'op_type': 'c', 'strike': call_nearestStrike+50 , 'tr_type': 's', 'op_pr': df_tmp1.loc[call_nearestStrike+50]['lastPrice']}
            op3={'op_type': 'c', 'strike': call_nearestStrike+150 , 'tr_type': 's', 'op_pr': df_tmp1.loc[call_nearestStrike+150]['lastPrice']}
            op_list=[op1, op2, op3]
            callOptionString1="Nifty Index Expiry "+ str(df_call['expiryDate'][0]) + "Buy 1 lot CE-Strike " + str(call_nearestStrike) + " @" + str(df_tmp1.loc[call_nearestStrike]['lastPrice'])
            callOptionString2="Nifty Index Expiry "+ str(df_call['expiryDate'][0]) + "Sell 1 lot CE-Strike " + str(call_nearestStrike+50) + " @" + str(df_tmp1.loc[call_nearestStrike+50]['lastPrice'])
            callOptionString3="Nifty Index Expiry "+ str(df_call['expiryDate'][0]) + "Sell 1 lot CE-Strike " + str(call_nearestStrike+150) + " @" + str(df_tmp1.loc[call_nearestStrike+150]['lastPrice'])
            htmltemplate = htmltemplate + "<h4> " + callOptionString1 + callOptionString2 + callOptionString3 + "</h4>"
            op.multi_plotter(spot=nfSpot,spot_range=2, op_list=op_list, save=True,file="plot8.png")          
            file_path=os.getcwd() + "\\plot8.png"
            block_blob_service.create_blob_from_path(
            mycontainer,
            "plot8.png",
            file_path,
            content_settings=ContentSettings(content_type='image/png')
            )
            
            htmltemplate= htmltemplate + "<h4> Put Straddle -Buy 1 lot of Nifty Put at the money Strike Price " + str(put_nearestStrike) + " and sell 1 lot of Nifty Put at Strike Price " + str(put_nearestStrike-50) + " and sell another 1 lot of Nifty Put at Strike Price " + str(put_nearestStrike-150)+ " hold the position till expiry if Nifty trend is negative or exit if trend is positive. Risk is however minimal </h4>"
            op1={'op_type': 'p', 'strike': put_nearestStrike , 'tr_type': 'b', 'op_pr': df_tmp2.loc[put_nearestStrike]['lastPrice']}
            op2={'op_type': 'p', 'strike': put_nearestStrike-50 , 'tr_type': 's', 'op_pr': df_tmp2.loc[put_nearestStrike-50]['lastPrice']}
            op3={'op_type': 'p', 'strike': put_nearestStrike-100 , 'tr_type': 's', 'op_pr': df_tmp2.loc[put_nearestStrike-150]['lastPrice']}
            
            op_list=[op1, op2, op3]
            putOptionString1="Nifty Index Expiry "+ str(df_call['expiryDate'][0]) + "Buy 1 lot PE-Strike " + str(put_nearestStrike) + " @" + str(df_tmp2.loc[put_nearestStrike]['lastPrice'])
            putOptionString2="Nifty Index Expiry "+ str(df_call['expiryDate'][0]) + "Sell 1 lot PE-Strike " + str(put_nearestStrike-50) + " @" + str(df_tmp2.loc[put_nearestStrike-50]['lastPrice'])
            putOptionString3="Nifty Index Expiry "+ str(df_call['expiryDate'][0]) + "Sell 1 lot PE-Strike " + str(put_nearestStrike-150) + " @" + str(df_tmp2.loc[put_nearestStrike-150]['lastPrice'])
            htmltemplate = htmltemplate + "<h4> " + putOptionString1 + putOptionString2 + putOptionString3+ "</h4>"
            op.multi_plotter(spot=nfSpot,spot_range=2, op_list=op_list, save=True,file="plot9.png")
            del(df_tmp1)
            del(df_tmp2)            
            file_path=os.getcwd() + "\\plot9.png"
            block_blob_service.create_blob_from_path(
            mycontainer,
            "plot9.png",
            file_path,
            content_settings=ContentSettings(content_type='image/png')
            )
            
            htmltemplate = htmltemplate + "<h5> <img src='https://testoptable.blob.core.windows.net/testop/plot9.png' /> </h5>"
            entity["testvale"] = htmltemplate
            entity["currday"] = todaydt_global
            table.update_entity(mode=UpdateMode.MERGE, entity=entity)            
            
        elif curday == "Thursday":
            htmltemplate= htmltemplate + "<h3> Plain Vanilla Call Short and Put short option at one of the highest OI for decay on expiry </h3>"
            df_tmp_call=df_call['openInterest'].nlargest(2).to_numpy()
            df_tmp_put=df_put['openInterest'].nlargest(2).to_numpy()
            df_tmp1=df_call.copy()
            df_tmp1.set_index('strikePrice', inplace=True)
            call_nearestStrike1=call_nearestStrike.copy()
            while df_tmp1.loc[call_nearestStrike1]['openInterest'] not in df_tmp_call:
                call_nearestStrike1=call_nearestStrike1+50
            
            df_tmp2=df_put.copy()
            df_tmp2.set_index('strikePrice', inplace=True)
            put_nearestStrike1=put_nearestStrike.copy()
            while df_tmp2.loc[put_nearestStrike1]['openInterest'] not in df_tmp_put:
                put_nearestStrike1=put_nearestStrike1-50
              
            op1={'op_type': 'c', 'strike': call_nearestStrike1 , 'tr_type': 's', 'op_pr': df_tmp1.loc[call_nearestStrike1]['lastPrice']}
            op2={'op_type': 'p', 'strike': put_nearestStrike1, 'tr_type': 's', 'op_pr': df_tmp2.loc[put_nearestStrike1]['lastPrice']}
    
            op_list=[op1, op2]
            htmltemplate= htmltemplate + "<h4>Sell 1 lot of Nifty Call at Strike Price " + str(call_nearestStrike1) + " and 1 lot of Nifty Put at Strike Price " + str(put_nearestStrike1) + " only for expiry day </h4>"
            nfSpot=df_call['underlyingValue'][0]
            callOptionString="Nifty Index Expiry "+ str(df_call['expiryDate'][0]) + "Sell 1 lot CE-Strike " + str(call_nearestStrike1) + " @" + str(df_tmp1.loc[call_nearestStrike1]['lastPrice'])
            putOptionString="Nifty Index Expiry "+ str(df_put['expiryDate'][0]) + "Sell 1 lot PE-Strike " + str(put_nearestStrike1) + " @" + str(df_tmp1.loc[put_nearestStrike1]['lastPrice'])
            htmltemplate = htmltemplate + "<h4> " + callOptionString + putOptionString +"</h4>"
            op.multi_plotter(spot=nfSpot,spot_range=1, op_list=op_list, file="plot1.png")
            file_path=os.getcwd() + "\\plot1.png"
            block_blob_service.create_blob_from_path(
            mycontainer,
            "plot1.png",
            file_path,
            content_settings=ContentSettings(content_type='image/png')
            )
            
            htmltemplate = htmltemplate + "<h5> <img src='https://testoptable.blob.core.windows.net/testop/plot1.png' /> </h5>"
            del(call_nearestStrike1,put_nearestStrike1)
            del(df_tmp1)
            del(df_tmp2)
            entity["testvale"] = htmltemplate
            entity["currday"] = todaydt_global
            table.update_entity(mode=UpdateMode.MERGE, entity=entity)            
    else:
        htmltemplate=entity['testvale']
    return htmltemplate