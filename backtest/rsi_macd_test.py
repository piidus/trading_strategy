
import backtrader as bt
import datetime  # For datetime objects
import os.path  # To manage paths
import sys  # To find out the script name (in argv[0])
# because it could have been called from anywhere
modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.append(modpath)
print(modpath)
cerebro = bt.Cerebro()
cerebro.broker.setcash(100000.0)
if __name__ == '__main__':
    

    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    cerebro.run()

    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())