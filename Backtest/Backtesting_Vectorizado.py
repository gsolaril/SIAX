import os
import numpy
import pandas
import time
import matplotlib
import IPython

class Backtest:

    ##########################################################################
    def __init__(self, Dataset, deposit = 10000, PS = 0.01, PV = 1, minLot = 0.01):
        self.Deposit = deposit  # Capital inicial.
        self.Dataset = numpy.floor(Dataset.copy()/PS)*PS # Copia de dataset, redondeado a "PS".
        self.Dataset[["$", "Delays"]] = None # Nuevas columnas, a llenar durante el backtest.
        self.Symbol = {"PS": PS, "PV": PV, "PP": PV/PS, "minLot": minLot} # Especificaciones.
        self.Active = pandas.DataFrame(columns = ["OT", "OP", "Type", "Lot", "SL", "TP"])
        self.Trades = pandas.DataFrame(columns = ["OT", "CT", "OP", "CP", "Type", "Lot",
                                                  "Cause", "Points", "Profit", "Return"])
        self.Allow_Sgn_Close = True

    ##########################################################################
    def trade_open(self, signal, invest):  # "invest": máx USD a perder en SL.
        OT, OP, Type, Size, SL, TP = signal.values()  # Recupero valores de señal.
        if (Type == None): return  # Si no detecto ninguna señal, no hago nada.
        max_loss = abs(OP - SL)*self.Symbol["PP"]  # Mi tolerancia en puntos.
        minLot = self.Symbol["minLot"]  # Número de lote mínimo permisible.
        lot = max(minLot, Size*invest/max_loss)  # Número de lote.
        lot = numpy.floor(lot/minLot)*minLot # Hacer múltiplo de minLot.
        # Armo la fila y la agrego AL FINAL ("len self.Active") del dataframe:
        self.Active.loc[len(self.Active), :] = [OT, OP, Type, lot, SL, TP] 

    ##########################################################################
    def trade_check(self, signal, trade, row, row_1):
        Type, SL, TP = trade[["Type", "SL", "TP"]] # Datos de operación ya abierta.
        # Si signal/trade es buy (+1) y trade/signal es (-1), es True:
        is_sgn_close = self.Allow_Sgn_Close and (signal["Type"] != Type)
        stop = signal["OP"] if is_sgn_close else None  # Si se cumple, obtener precio.
        stop = "TP" if (row["Low"] <= TP <= row["High"]) else stop # Si se cumple, "TP".
        stop = "TP" if (row["Open"] <= TP <= row_1["Close"]) else stop  # Gap hacia abajo.
        stop = "TP" if (row["Open"] >= TP >= row_1["Close"]) else stop  # Gap hacia arriba.
        stop = "SL" if (row["Low"] <= SL <= row["High"]) else stop # Si se cumple, "SL"
        stop = "TP" if (row["Open"] <= SL <= row_1["Close"]) else stop  # Gap hacia abajo.
        stop = "TP" if (row["Open"] >= SL >= row_1["Close"]) else stop  # Gap hacia arriba.
        return stop # Puede dar el string "SL", el string "TP", el float OP, o None.

    ##########################################################################
    def trade_close(self, stop, CT, n_trade):
        if (stop == None): return 0  # No se encuentra en condiciones de cerrar.
        if (len(self.Active) <= 0): return  # No hay operaciones a cerrar.
        Trade = self.Active.iloc[n_trade, :]  # Copiar información de operación.
        OT, OP, Type, Lot, SL, TP = Trade  
        self.Active.drop(index = n_trade, inplace = True)  # Borrar fila.
        self.Active.reset_index(inplace = True)  # Resetear números de fila.
        self.Active.drop(columns = "index", inplace = True)  # Borrar números viejos.
        # "Closing Price": Valores de SL/TP o precio de señal, acorde del caso.
        CP = SL if (stop == "SL") else (TP if (stop == "TP") else stop)
        if isinstance(stop, float): stop = "Signal"  # Si cerró por señal, etiquetar.
        points = Type*(CP - OP)/self.Symbol["PS"]  # Ganancia medida en puntos.
        profit = Lot*points*self.Symbol["PV"]  # Ganancia medida en USD.
        rets = profit/self.Dataset.loc[CT, "$"]  # Ganancia relativa.
        rets = str(numpy.floor(rets*1e4)/1e2) + "%"  # Expresar en porcentaje!
        # Construir fila de trade cerrado, y agregar al final de ".Trades".
        New = [OT, CT, OP, CP, Type, Lot, stop, points, profit, rets]
        self.Trades.loc[len(self.Trades), :] = New
        return profit  # La función devuelve la ganancia en USD como salida.

    ##########################################################################
    def run(self, Strategy, compound = 0, risk = 0.01, max_trades = 3):
        capital = self.Deposit  # Capital inicial.
        self.Active = self.Active[0:0]  # Limpieza/reseteo de dataframe.
        self.Trades = self.Trades[0:0]  # Limpieza/reseteo de dataframe.
        self.Dataset[Strategy.Indicators] = None # Columnas para indicadores.
        for nr in range(Strategy.minRows, len(self.Dataset)):
            if (capital <= 0): break  # Si me quedo sin $$, no puedo seguir.
            before = time.time()  # Tomo nota de la hora actual.
            t = self.Dataset.index[nr]  # Fecha/hora de la fila actual "nr".
            t1 = self.Dataset.index[nr - 1] # Fecha/hora de la fila anterior.
            nr0 = nr - Strategy.minRows  # 1ª fila del bloque a dar a "call".
            t0 = self.Dataset.index[nr0]  # Fecha/hora de la primera fila "nr0".
            Row = self.Dataset.loc[t, :]  # Datos de fila actual.
            Row1 = self.Dataset.loc[t1, :] # Datos de fila inmediatamente anterior.
            Rows = self.Dataset.loc[t0 : t, :]  # Bloque de filas para "call".
            Ind, Signal = Strategy.call(Rows)  # Output de "call" de estrategia.
            self.Dataset.loc[t, "$"] = capital  # Tomo nota de capital actual.
            self.Dataset.loc[t, Ind] = Ind.values()  # Valores de indicadores.
            delay = 1000000*(time.time() - before)  # Delay en microsegundos.
            self.Dataset.loc[t, "Delays"] = 1234#delay
            n_trade = 0  # Comienzo monitoreo de trades desde primera fila.
            while True:  # Mientras queden trades abiertos por monitorear...
                try: Trade = self.Active.iloc[n_trade, :]  # Tomo info de trade.
                except: break # Sin mas trades activos por ahora.
                # Comparo con fila de dataset actual, y veo si está para cerrar:
                stop = self.trade_check(Signal, Trade, Row, Row1)
                # Si está para cerrar, me devuelve la ganancia. Sino, devuelve 0.
                profit = self.trade_close(stop, t, n_trade)  # Cierro operación.
                capital = capital + profit  # Sumo ganancia a "capital".
                self.Dataset.loc[t, "$"] = capital  # Guardo valor en dataset.
                # Si la actual operación no debió cerrar, analizo la siguiente.
                if (stop == None): n_trade = n_trade + 1
            # Si me queda capital y espacio para nuevas operaciones...
            if (capital > 0) and (len(self.Active) < max_trades):
                # Decido cuanto voy a arriesgar de mi capital actual.
                reinvest = (capital - self.Deposit)*compound #| Ver arriba para
                invest = (self.Deposit + reinvest)*risk      #| ...mas detalles.
                # Tomo la señal devuelta por la estrategia, y la hago operación.
                self.trade_open(Signal, invest)
        # Si terminé el dataset y quedaron operaciones abiertas en ".Active"...
        while not self.Active.empty:
            close = Row["Close"] # Tomo al último close como precio de cierre.
            capital = capital + self.trade_close(close, t, 0)
        self.Dataset.loc[t, "$"] = capital # Guardo al capital final.

    ##########################################################################
    def plot(self, indicators = True, capital = True,
                     trades = True, x1 = 0, x2 = 1):
        T = self.Dataset.index
        Figure, Axes = matplotlib.pyplot.subplots();
        Figure.set_figwidth(13) ; Figure.set_figheight(5)
        H, L, C = self.Dataset[["High", "Low", "Close"]].values.T
        Axes.plot(T, C, color = "white", linewidth = 2)
        Axes.fill_between(T, H, L, facecolor = "gray")
        Axes.set_ylabel("Prices", fontweight = "bold")
        colors = ["c", "y", "m", "pink", "teal", "coral"]
        if indicators:
            for label in self.Dataset.columns[8:]:
                if (label[0] == "^"): continue
                Axes.plot(T, self.Dataset[label], label = label, zorder = 8,
                                       color = colors.pop(0), linewidth = 3)
        if trades:
            for index in self.Trades.index:
                OT, CT, OP, CP = self.Trades.loc[index].iloc[:4]
                dt = self.Dataset.index[-1] - self.Dataset.index[0]
                LT = CT - dt/50
                won = (self.Trades["Profit"][index] > 0)
                Axes.plot([OT, CT, LT], [OP, CP, CP], lw = 3, zorder = 9,
                                   color = "limegreen" if won else "red")
                Axes.scatter(OT, OP, s = 50, marker = "o", zorder = 10,
                                   color = "lime" if won else "tomato")
        if capital:
            Axes2 = Axes.twinx()  ;  Axes2.grid(False)
            Axes2.tick_params(axis = "y", colors = "lime")
            Axes2.plot(T, self.Dataset["$"], "--", color = "lime", lw = 4)
            Axes2.set_ylim(ymin = 0, ymax = Axes2.get_ylim()[1])
            Axes2.set_ylabel("Capital", fontweight = "bold", color = "lime")
        t1 = self.Dataset.index[int(min(x1, x2)*len(self.Dataset))]
        t2 = self.Dataset.index[int(max(x1, x2)*len(self.Dataset)) - 1]
        Axes.set_xlim(xmin = t1, xmax = t2)
        Axes.legend()
        return Axes
        
    ##########################################################################    PENDIENTE, A TERMINAR
    def stats(self):
        if self.Trades.empty: return
        columns = ["Points", "Profit", "Return"]
        Stats = pandas.DataFrame(columns = columns)
        trades_won = (self.Trades["Points"] > 0)
        trades_lost = (self.Trades["Points"] < 0)
        for column in columns[::-1]:
            if (column == "Return"):
                remove_pct = lambda x: x.rstrip("%")
                self.Trades["Return"] = self.Trades["Return"].map(remove_pct)
                self.Trades["Return"] = self.Trades["Return"].astype(float)
            Stats.loc["Trades", column] = len(self.Trades)
            Stats.loc["Trades :)", column] = trades_won.sum()
            Stats.loc["Trades :(", column] = trades_lost.sum()
            Stats.loc["Mean Net",  column] = self.Trades.loc[:, column].mean()
            Stats.loc["StDev Net", column] = self.Trades.loc[:, column].std()
            Stats.loc["Mean :)",   column] = self.Trades.loc[trades_won,  column].mean()
            Stats.loc["StDev :)",  column] = self.Trades.loc[trades_won,  column].std()
            Stats.loc["Mean :(",   column] = self.Trades.loc[trades_lost, column].mean()
            Stats.loc["StDev :(",  column] = self.Trades.loc[trades_lost, column].std()
            try: Sharpe = Stats[column]["Mean Net"]/Stats[column]["StDev Net"]
            except: Sharpe = numpy.nan ## Por si "StDev = 0" en denominador.
            try: Sortino = Stats[column]["Mean Net"]/Stats[column]["StDev :("]
            except: Sortino = numpy.nan ## Por si "StDev = 0" en denominador.
            Stats.loc["Sharpe",   column] = Sharpe
            Stats.loc["Sortino",  column] = Sortino
            Stats.loc["Sharpe N", column] = Sharpe*len(self.Trades)**(1/2)
            if (column == "Return"):
                self.Trades["Return"] = self.Trades["Return"].astype(str) + "%"
        return Stats