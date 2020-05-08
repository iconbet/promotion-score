from iconservice import *

TAG = 'Promotion'

TEN_18 = 1000000000000000000
WAGER_WAR_PRIZE = [25, 20, 15, 10, 10, 6, 6, 3, 3, 2]


# An interface of rewards score to get daily wagers
class RewardsInterface(InterfaceScore):
    @interface
    def get_daily_wager_totals(self) -> str:
        pass


class Promotion(IconScoreBase):

    _REWARDS_SCORE = "rewards_score"
    _DIVIDENDS_SCORE = "dividends_score"
    _TOTAL_PRIZES = "total_prizes"

    @eventlog(indexed=2)
    def FundTransfer(self, to: str, amount: int, note: str):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._rewards_score = VarDB(self._REWARDS_SCORE, db, value_type=Address)
        self._dividends_score = VarDB(self._DIVIDENDS_SCORE, db, value_type=Address)
        self._total_prizes = VarDB(self._TOTAL_PRIZES, db, value_type=int)

    def on_install(self) -> None:
        super().on_install()
        self._total_prizes.set(0)

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=True)
    def name(self) -> str:
        return "ICONbet Promotion"

    @external
    def set_rewards_score(self, _score: Address) -> None:
        """
        Sets the rewards core address. Only owner can set the address
        :param _score: Address of the rewards score
        :type _score: :class:`iconservice.base.address.Address`
        :return:
        """
        if self.msg.sender == self.owner:
            self._rewards_score.set(_score)

    @external(readonly=True)
    def get_rewards_score(self) -> Address:
        """
        Returns the Rewards score address
        :return: Address of the rewards score
        :rtype: :class:`iconservice.base.address.Address`
        """
        return self._rewards_score.get()

    @external
    def set_dividends_score(self, _score: Address) -> None:
        """
        Sets the dividends score address. Only owner can set the address
        :param _score: Address of the dividends score
        :type _score: :class:`iconservice.base.address.Address`
        :return:
        """
        if self.msg.sender == self.owner:
            self._dividends_score.set(_score)

    @external(readonly=True)
    def get_dividends_score(self) -> Address:
        """
        Returns the dividends score address
        :return: Address of the dividends score
        :rtype: :class:`iconservice.base.address.Address`
        """
        return self._dividends_score.get()

    def _distribute_prizes(self) -> None:
        """
        Distributes the prizes it receive to the top 10 wagerers
        :return:
        """
        rewards_score = self.create_interface_score(self._rewards_score.get(), RewardsInterface)
        wager_totals = json_loads(rewards_score.get_daily_wager_totals())
        wagers = wager_totals["yesterday"]
        top_ten = sorted(zip(wagers.values(), wagers.keys()), key=lambda wager: -wager[0])[:10]
        total_percent = sum(WAGER_WAR_PRIZE[:len(top_ten)])
        total_prizes = self._total_prizes.get()
        for i in range(len(top_ten)):
            address = top_ten[i][1]
            prize = WAGER_WAR_PRIZE[i] * total_prizes // total_percent
            total_percent -= WAGER_WAR_PRIZE[i]
            total_prizes -= prize
            try:
                self.icx.transfer(Address.from_string(address), prize)
                self.FundTransfer(address, prize, "Wager Wars prize distribution")
            except BaseException as e:
                revert(f'Network problem. '
                       f'Prize not sent. '
                       f'Will try again later. '
                       f'Exception: {e}')
        self._total_prizes.set(0)

    @payable
    def fallback(self) -> None:
        if self.msg.sender == self._dividends_score.get():
            self._total_prizes.set(self.msg.value)
            self._distribute_prizes()
        else:
            revert("Funds can only be accepted from the dividends distribution contract")