// stream processor which reads trades from the RT stream and writes them to a KDB+ table

base:.qsp.v2.read.fromStream["rawTrade";"data"]
    .qsp.map[{[data] `time`spTime xcols update spTime:.z.P from data}]
    .qsp.split[]

rawTrade:base .qsp.v2.write.toDatabase[`trade; .qsp.use (!) . flip (
      (`database     ; "kxi");
      (`overwrite   ; 1b)
      )]

ohlc:base .qsp.window.timer[00:00:10]
    .qsp.map[{[data] 
      select time:last time,
        sym:last sym,
        high:max price, 
        low:min price,
        open:first price, 
        close:last price,
        volume:sum size
      from data
      where sym=`AAPL
      }]
    .qsp.v2.write.toDatabase[`ohlc; .qsp.use (!) . flip (
      (`database     ; "kxi");
      (`overwrite   ; 1b)
      )]

.qsp.run (rawTrade, ohlc)