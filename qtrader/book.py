from bintrees import FastRBTree
from pandas import DataFrame


'''
Begin help functions
'''


class DifferentPriceException(Exception):
    """
    DifferentPriceException is raised by the update() method in the PriceLevel
    class to indicate that the price of order object is different from the
    PriceLevel
    """
    pass


class InvalidTypeException(Exception):
    """
    InvalidTypeException is raised by the init() method in the Bookside
    class to indicate that the the book type chose is invalid
    """
    pass


'''
End help functions
'''


class Order(object):
    '''
    A representation of a single Order
    '''
    def __init__(self, d_msg):
        '''
        Instantiate a Order object. Save all parameter as attributes
        :param d_msg: dictionary.
        '''
        # keep data extract from file
        self.d_msg = d_msg.copy()
        self.d_msg['org_total_qty_order'] = self.d_msg['total_qty_order']
        f_q1 = self.d_msg['total_qty_order']
        f_q2 = self.d_msg['traded_qty_order']
        self.d_msg['total_qty_order'] = f_q1 - f_q2
        self.order_id = d_msg['order_id']
        self.new_order_id = d_msg['new_order_id']
        self.name = "{:07d}".format(d_msg['order_id'])
        self.main_id = self.order_id

    def __str__(self):
        '''
        Return the name of the Order
        '''
        return self.name

    def __repr__(self):
        '''
        Return the name of the Order
        '''
        return self.name

    def __eq__(self, other):
        '''
        Return if a Order has equal order_id from the other
        :param other: Order object. Order to be compared
        '''
        return self.order_id == other.order_id

    def __ne__(self, other):
        '''
        Return if a Order has different order_id from the other
        :param other: Order object. Order to be compared
        '''
        return not self.__eq__(other)

    def __hash__(self):
        '''
        Allow the Order object be used as a key in a hash table. It is used by
        dictionaries
        '''
        return self.order_id.__hash__()

    def __getitem__(self, s_key):
        '''
        Allow direct access to the inner dictionary of the object
        :param i_index: integer. index of the l_legs attribute list
        '''
        return self.d_msg[s_key]


class PriceLevel(object):
    '''
    A representation of a Price level in the book
    '''
    def __init__(self, f_price):
        '''
        A representation of a PriceLevel object
        '''
        self.f_price = f_price
        self.i_qty = 0
        self.order_tree = FastRBTree()

    def add(self, order_aux):
        '''
        Insert the information in the tree using the info in order_aux. Return
        is should delete the Price level or not
        :param order_aux: Order Object. The Order message to be updated
        '''
        # check if the order_aux price is the same of the self
        s_status = order_aux['order_status']
        if order_aux['order_price'] != self.f_price:
            raise DifferentPriceException
        elif s_status in ['New', 'Replaced', 'Partially Filled']:
            self.order_tree.insert(order_aux.main_id, order_aux)
            self.i_qty += int(order_aux['total_qty_order'])
        # check if there is no object in the updated tree (should be deleted)
        return self.order_tree.count == 0

    def delete(self, i_last_id, i_old_qty):
        '''
        Delete the information in the tree using the info in order_aux. Return
        is should delete the Price level or not
        :param i_last_id: Integer. The previous secondary order id
        :param i_old_qty: Integer. The previous order qty
        '''
        # check if the order_aux price is the same of the self
        try:
            self.order_tree.remove(i_last_id)
            self.i_qty -= i_old_qty
        except KeyError:
            raise DifferentPriceException
        # check if there is no object in the updated tree (should be deleted)
        return self.order_tree.count == 0

    def __str__(self):
        '''
        Return the name of the PriceLevel
        '''
        return '{:,.0f}'.format(self.i_qty)

    def __repr__(self):
        '''
        Return the name of the PriceLevel
        '''
        return '{:,.0f}'.format(self.i_qty)

    def __eq__(self, other):
        '''
        Return if a PriceLevel has equal price from the other
        :param other: PriceLevel object. PriceLevel to be compared
        '''
        # just to make sure that there is no floating point discrepance
        f_aux = other
        if not isinstance(other, float):
            f_aux = other.f_price
        return abs(self.f_price - f_aux) < 1e-4

    def __gt__(self, other):
        '''
        Return if a PriceLevel has a gerater price from the other.
        Bintrees uses that to compare nodes
        :param other: PriceLevel object. PriceLevel to be compared
        '''
        # just to make sure that there is no floating point discrepance
        f_aux = other
        if not isinstance(other, float):
            f_aux = other.f_price
        return (f_aux - self.f_price) > 1e-4

    def __lt__(self, other):
        '''
        Return if a Order has smaller order_id from the other. Bintrees uses
        that to compare nodes
        :param other: Order object. Order to be compared
        '''
        f_aux = other
        if not isinstance(other, float):
            f_aux = other.f_price
        return (f_aux - self.f_price) < -1e-4

    def __ne__(self, other):
        '''
        Return if a Order has different order_id from the other
        :param other: Order object. Order to be compared
        '''
        return not self.__eq__(other)


class BookSide(object):
    '''
    A side of the lmit order book representation
    '''
    def __init__(self, s_side):
        '''
        Initialize a BookSide object. Save all parameters as attributes
        :param s_side: string. BID or ASK
        '''
        if s_side not in ['BID', 'ASK']:
            raise InvalidTypeException('side should be BID or ASK')
        self.s_side = s_side
        self.price_tree = FastRBTree()
        self._i_idx = 0
        self.d_order_map = {}
        self.last_price = 0.

    def update(self, d_data):
        '''
        Update the state of the order book given the data pased. Return if the
        message was handle successfully
        :param d_data: dict. data related to a single order
        '''
        # dont process aggresive trades
        if d_data['agressor_indicator'] == 'Agressive':
            return True
        # update the book information
        order_aux = Order(d_data)
        s_status = order_aux['order_status']
        b_sould_update = True
        b_success = True
        # check the order status
        if s_status != 'New':
            try:
                i_old_id = self.d_order_map[order_aux]['main_id']
            except KeyError:
                if s_status == 'Canceled' or s_status == 'Filled':
                    b_sould_update = False
                    s_status = 'Invalid'
                elif s_status == 'Replaced':
                    s_status = 'New'
        # process the message
        if s_status == 'New':
            b_sould_update = self._new_order(order_aux)
        elif s_status != 'Invalid':
            i_old_id = self.d_order_map[order_aux]['main_id']
            f_old_pr = self.d_order_map[order_aux]['price']
            i_old_q = self.d_order_map[order_aux]['qty']
            # hold the last traded price
            if s_status in ['Partially Filled', 'Filled']:
                self.last_price = order_aux['order_price']
            # process message
            if s_status in ['Canceled', 'Expired', 'Filled']:
                b_sould_update = self._canc_expr_filled_order(order_aux,
                                                              i_old_id,
                                                              f_old_pr,
                                                              i_old_q)
                if not b_sould_update:
                    b_success = False
            elif s_status == 'Replaced':
                b_sould_update = self._replaced_order(order_aux,
                                                      i_old_id,
                                                      f_old_pr,
                                                      i_old_q)
            elif s_status == 'Partially Filled':
                b_sould_update = self._partially_filled(order_aux,
                                                        i_old_id,
                                                        f_old_pr,
                                                        i_old_q)
        # remove from order map
        if s_status not in ['New', 'Invalid']:
            self.d_order_map.pop(order_aux)
        # update the order map
        if b_sould_update:
            f_qty = int(order_aux['total_qty_order'])
            self.d_order_map[order_aux] = {}
            self.d_order_map[order_aux]['price'] = d_data['order_price']
            self.d_order_map[order_aux]['order_id'] = order_aux.order_id
            self.d_order_map[order_aux]['qty'] = f_qty
            self.d_order_map[order_aux]['main_id'] = order_aux.main_id

        # return that the update was done
        return True

    def _canc_expr_filled_order(self, order_obj, i_old_id, f_old_pr, i_old_q):
        '''
        Update price_tree when passed canceled, expried or filled orders
        :param order_obj: Order Object. The last order in the file
        :param i_old_id: integer. Old id of the order_obj
        :param f_old_pr: float. Old price of the order_obj
        :param i_old_q: integer. Old qty of the order_obj
        '''
        this_price = self.price_tree.get(f_old_pr)
        if this_price.delete(i_old_id, i_old_q):
            self.price_tree.remove(f_old_pr)
        # remove from order map
        return False

    def _replaced_order(self, order_obj, i_old_id, f_old_pr, i_old_q):
        '''
        Update price_tree when passed replaced orders
        :param order_obj: Order Object. The last order in the file
        :param i_old_id: integer. Old id of the order_obj
        :param f_old_pr: float. Old price of the order_obj
        :param i_old_q: integer. Old qty of the order_obj
        '''
        # remove from the old price
        this_price = self.price_tree.get(f_old_pr)
        if this_price.delete(i_old_id, i_old_q):
            self.price_tree.remove(f_old_pr)

        # insert in the new price
        f_price = order_obj['order_price']
        if not self.price_tree.get(f_price):
            self.price_tree.insert(f_price, PriceLevel(f_price))
        # insert the order in the due price
        this_price = self.price_tree.get(f_price)
        this_price.add(order_obj)
        return True

    def _partially_filled(self, order_obj, i_old_id, f_old_pr, i_old_q):
        '''
        Update price_tree when passed partially filled orders
        :param order_obj: Order Object. The last order in the file
        :param i_old_id: integer. Old id of the order_obj
        :param f_old_pr: float. Old price of the order_obj
        :param i_old_q: integer. Old qty of the order_obj
        '''
        # delete old price, if it is needed
        this_price = self.price_tree.get(f_old_pr)
        if this_price.delete(i_old_id, i_old_q):
            self.price_tree.remove(f_old_pr)

        # add/modify order
        # insert in the new price
        f_price = order_obj['order_price']
        if not self.price_tree.get(f_price):
            self.price_tree.insert(f_price, PriceLevel(f_price))
        this_price = self.price_tree.get(f_price)
        this_price.add(order_obj)
        return True

    def _new_order(self, order_obj):
        '''
        Update price_tree when passed new orders
        :param order_obj: Order Object. The last order in the file
        '''
        # if it was already in the order map
        if order_obj in self.d_order_map:
            i_old_sec_id = self.d_order_map[order_obj]['last_order_id']
            f_old_price = self.d_order_map[order_obj]['price']
            i_old_qty = self.d_order_map[order_obj]['qty']
            this_price = self.price_tree.get(f_old_price)
            # remove from order map
            self.d_order_map.pop(order_obj)
            if this_price.delete(i_old_sec_id, i_old_qty):
                self.price_tree.remove(f_old_price)

        # insert a empty price level if it is needed
        f_price = order_obj['order_price']
        if not self.price_tree.get(f_price):
            self.price_tree.insert(f_price, PriceLevel(f_price))
        # add the order
        this_price = self.price_tree.get(f_price)
        this_price.add(order_obj)

        return True

    def get_n_top_prices(self, n):
        '''
        Return a dataframe with the N top price levels
        :param n: integer. Number of price levels desired
        '''
        raise NotImplementedError

    def get_n_botton_prices(self, n=5):
        '''
        Return a dataframe with the N botton price levels
        :param n: integer. Number of price levels desired
        '''
        raise NotImplementedError


class BidSide(BookSide):
    '''
    The BID side of the limit order book representation
    '''
    def __init__(self):
        '''
        Initialize a BidSide object.
        '''
        super(BidSide, self).__init__('BID')

    def get_n_top_prices(self, n, b_return_dataframe=True):
        '''
        Return a dataframe with the N top price levels
        :param n: integer. Number of price levels desired
        :param b_return_dataframe: boolean. If should return a dataframe
        '''
        t_rtn = self.price_tree.nlargest(n)
        if not b_return_dataframe:
            return t_rtn
        df_rtn = DataFrame(t_rtn)
        df_rtn.columns = ['PRICE', 'QTY']
        return df_rtn

    def get_n_botton_prices(self, n, b_return_dataframe=True):
        '''
        Return a dataframe with the N botton price levels
        :param n: integer. Number of price levels desired
        :param b_return_dataframe: boolean. If should return a dataframe
        '''
        t_rtn = self.price_tree.nsmallest(n)
        if not b_return_dataframe:
            return t_rtn
        df_rtn = DataFrame(t_rtn)
        df_rtn.columns = ['PRICE', 'QTY']
        return df_rtn


class AskSide(BookSide):
    '''
    The ASK side of the limit order book representation
    '''
    def __init__(self):
        '''
        Initialize a AskSide object.
        '''
        super(AskSide, self).__init__('ASK')

    def get_n_top_prices(self, n, b_return_dataframe=True):
        '''
        Return a dataframe with the N top price levels
        :param n: integer. Number of price levels desired
        :param b_return_dataframe: boolean. If should return a dataframe
        '''
        t_rtn = self.price_tree.nsmallest(n)
        if not b_return_dataframe:
            return t_rtn
        df_rtn = DataFrame(t_rtn)
        df_rtn.columns = ['PRICE', 'QTY']
        return df_rtn

    def get_n_botton_prices(self, n, b_return_dataframe=True):
        '''
        Return a dataframe with the N botton price levels
        :param n: integer. Number of price levels desired
        :param b_return_dataframe: boolean. If should return a dataframe
        '''
        t_rtn = self.price_tree.nlargest(n)
        if not b_return_dataframe:
            return t_rtn
        df_rtn = DataFrame(t_rtn)
        df_rtn.columns = ['PRICE', 'QTY']
        return df_rtn


class LimitOrderBook(object):
    '''
    A limit Order book representation. Keep the book sides synchronized
    '''
    def __init__(self, s_instrument):
        '''
        Initialize a LimitOrderBook object. Save all parameters as attributes
        :param s_instrument: string. name of the instrument of book
        '''
        # initiate attributes
        self.book_bid = BidSide()
        self.book_ask = AskSide()
        self.s_instrument = s_instrument
        self.f_time = 0
        self.s_time = ''
        self.stop_iteration = False
        self.stop_time = None
        self.i_last_order_id = 0
        # initiate control variables
        self.d_bid = {}  # hold the last information get from the file
        self.d_ask = {}  # hold the last information get from the file
        # initiate loop control variables
        self.i_read_bid = True
        self.i_read_ask = True
        self.i_get_new_bid = True
        self.i_get_new_ask = True
        self.i_sec_bid_greatter = True
        # best prices tracker
        self.f_top_bid = None
        self.f_top_ask = None

    def get_n_top_prices(self, n):
        '''
        Return a dataframe with the n top prices of the current order book
        :param n: integer. Number of price levels desired
        '''
        t_rtn1 = self.book_bid.get_n_top_prices(n, b_return_dataframe=False)
        t_rtn2 = self.book_ask.get_n_top_prices(n, b_return_dataframe=False)
        df1 = DataFrame(t_rtn1, columns=['Bid', 'qBid'])
        df2 = DataFrame(t_rtn2, columns=['Ask', 'qAsk'])
        df1 = df1.reset_index(drop=True)
        df2 = df2.reset_index(drop=True)
        df_rtn = df1.join(df2)
        df_rtn = df_rtn.ix[:, ['qBid', 'Bid', 'Ask', 'qAsk']]

        return df_rtn

    def get_best_price(self, s_side):
        '''
        Return the best price of the specified side
        :param s_side: string. The side of the book
        '''
        if s_side == 'BID':
            obj_aux = self.book_bid.get_n_top_prices(1, False)
            if obj_aux:
                return obj_aux[0][0]
        elif s_side == 'ASK':
            obj_aux = self.book_ask.get_n_top_prices(1, False)
            if obj_aux:
                return obj_aux[0][0]

    def get_orders_by_price(self, s_side, f_price=None, b_rtn_obj=False):
        '''
        Recover the orders from a specific price level
        :param s_side: string. The side of the book
        :*param f_price: float. The price level desired. If not set, return
            the best price
        :*param b_rtn_obj: bool. If return the price object or tree of orders
        '''
        # side of the order book
        obj_price = None
        if s_side == 'BID':
            if not f_price:
                f_price = self.get_best_price(s_side)
            obj_price = self.book_bid.price_tree.get(f_price)
        elif s_side == 'ASK':
            if not f_price:
                f_price = self.get_best_price(s_side)
            obj_price = self.book_ask.price_tree.get(f_price)
        # return the order tree
        if obj_price:
            if b_rtn_obj:
                return obj_price
            return obj_price.order_tree

    def get_basic_stats(self):
        '''
        Return the number of price levels and number of orders remain in the
        dictionaries and trees
        '''
        i_n_order_bid = len(list(self.book_bid.d_order_map.keys()))
        i_n_order_ask = len(list(self.book_ask.d_order_map.keys()))
        i_n_price_bid = len([x for x in list(self.book_bid.price_tree.keys())])
        i_n_price_ask = len([x for x in list(self.book_ask.price_tree.keys())])
        i_n_order_bid, i_n_order_ask, i_n_price_bid, i_n_price_ask
        d_rtn = {'n_order_bid': i_n_order_bid,
                 'n_order_ask': i_n_order_ask,
                 'n_price_bid': i_n_price_bid,
                 'n_price_ask': i_n_price_ask}
        return d_rtn

    def update(self, d_data):
        '''
        Update the book based on the message passed
        d_data: dictionary. Last message from the Environment
        '''
        # check if should stop iteration
        self.i_last_order_id = max(self.i_last_order_id, d_data['order_id'])
        if d_data['order_side'] == 'BID':
            self.d_bid = d_data.copy()
            return self.book_bid.update(d_data)
        elif d_data['order_side'] == 'ASK':
            self.d_ask = d_data.copy()
            return self.book_ask.update(d_data)
        return False
