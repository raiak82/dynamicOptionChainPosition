# Nifty Index Options & Strategy
Light weight application or utility to fetch near real time NSE feed Nifty Index Option Chain, calculate technical Option Greeks, Option Pain & Put Call ratio. This is coupled with other important and dependent data like Global indices, FII & India VIX to help one to decide on to few curated Nifty Index option strategy.

Curated option strategy is designed as per days left to expiry and real time Nifty Option Pain data

![High level Design](https://github.com/raiak82/dynamicOptionChainPosition/blob/main/Architecture.png?raw=true)

High level design of different core components built on Azure Cloud leveraging Azure server-less consumption based model, Azure blob container and storage tables
1) NSE option chain- fetch NSE option chain table of near expiry date along with other market dependent parameters
2) Option Greeks calculator ( Reference- https://github.com/quantsbin/Quantsbin)
3) Plots to show Option Pain and top 5 Call/Put option
4) Dynamic Option Strategy- curated option strategy (Reference for multi-option plotter https://github.com/hashABCD/opstrat

# Set up Instructions:

1) Install Visual Studio Code
2) Clone repository from github link- https://github.com/raiak82/dynamicOptionChainPosition.git
3) Open cloned project folder. From VS code terminal run "python -m venv <venv-name>"
4) Create Azure Blob storage account and create Blob Container (for storing plots created at run time) and Table storage (for storing html value of Dynamic Option Strategy as String in order to avoid multiple update on a single day)

![Azure Blob storage container](https://github.com/raiak82/dynamicOptionChainPosition/blob/main/BlobStoragecontainer.png?raw=true)

![Azure Table Storage](https://github.com/raiak82/dynamicOptionChainPosition/blob/main/TableStorage.png?raw=true)

5. Update Storage account key in the init.py and optionStrategy.py file
connection_string = "DefaultEndpointsProtocol=https;AccountName=testoptable;AccountKey=XXXXXXXXXXXXXXXXXXXX;EndpointSuffix=core.windows.net"
6. To run locally- from VSCode, click on Run->Start Debugging :)

![Debug locallyr](https://github.com/raiak82/dynamicOptionChainPosition/blob/main/localrun.png?raw=true)

![Sample Run](https://github.com/raiak82/dynamicOptionChainPosition/blob/main/SampleRun.png?raw=true)
