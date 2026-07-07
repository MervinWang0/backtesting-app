from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from collections import defaultdict

from base.models import FuturesContract, FuturesPriceHistory, ContinuousFuturesPriceHistory, ContinuousFuturesSeries

@dataclass(frozen=True)
class RollInstructions:
    roll_date: date
    from_contract: FuturesContract
    to_contract: FuturesContract

class ContinuousFuturesSeriesBuilder:
    '''
    Builds a continuous futures series
    '''

    def __init__(self, series: ContinuousFuturesSeries):
        self.series = series

    def build(self, start_date: date, end_date: date):
        contracts = self.get_contracts()

        if len(contracts) <2:
            raise RuntimeError(
                f"At least two contracts are needed"
            )
        
        prices = self.load_prices(
            contracts = contracts,
            start_date = start_date,
            end_date = end_date,
        )

        contracts = [contract for contract in contracts if prices.get(contract.id)]

        roll_instructions = self.calculate_roll_dates(
            contracts = contracts,
            price_map = prices
        )

        continuous_series = self.stitch_contracts(
            contracts = contracts,
            price_map=  prices,
            roll_instructions = roll_instructions,
            start_date = start_date,
            end_date = end_date,
        )

        ContinuousFuturesPriceHistory.objects.filter(
            series=self.series,).delete()
        
        ContinuousFuturesPriceHistory.objects.bulk_create(continuous_series, batch_size=1000)

        return len(continuous_series)

    def get_contracts(self) -> list[FuturesContract]:
        return list(
            FuturesContract.objects.filter(root_symbol = self.series.contract_symbol).order_by("expiry_date")
        )
    
    def load_prices(self, contracts: list[FuturesContract], start_date : date, end_date: date) -> dict[int, dict[date, FuturesPriceHistory]]:
        '''
        builds price mappings, contract_index : {date : FuturesPriceHistory}
        '''
        query = (FuturesPriceHistory.objects.filter(contract__in = contracts)
                                            .select_related("contract")
                                            .order_by("date"))
        query = query.filter(date__gte = start_date, date__lte = end_date)

        price_map = defaultdict(dict)

        for price in query.iterator():
            price_map[price.contract_id][price.date] = price
        
        return dict(price_map)
    
    def calculate_roll_dates(self, contracts: list[FuturesContract], price_map: dict[int, dict[date, FuturesPriceHistory]]) -> list[RollInstructions]:
        '''
        Decides when each current contract should be replaced by the next one
        '''

        roll_days = self.series.roll_days
        instructions: list[RollInstructions] = []

        for curr_contract, next_contract in zip(contracts, contracts[1:]):
            current_prices = price_map.get(curr_contract.id, {})

            next_prices = price_map.get(next_contract.id, {})

            current_trading_dates = sorted(price_date for price_date in current_prices if price_date <= curr_contract.expiry_date)
            
            if len(current_trading_dates) <= roll_days:
                raise RuntimeError(f"Not enough price history for {roll_days}")
            
            roll_index = len(current_trading_dates) -1 - roll_days

            planned_roll_date = current_trading_dates[roll_index]

            common_dates = sorted(price_date for price_date in (current_prices.keys() & next_prices.keys()) if price_date>=planned_roll_date and price_date <= curr_contract.expiry_date)

            if not common_dates:
                raise RuntimeError(
                    f"No common rollover date for "
                    f"{curr_contract.contract_code} -> "
                    f"{next_contract.contract_code} "
                    f"on or after {planned_roll_date}"
                )

            #Gets all available dates after the planned roll date
            next_available_dates = sorted(price_date for price_date in next_prices if price_date >= planned_roll_date)

            #Get actual date to rollover
            actual_roll_date = next_available_dates[0]

            instructions.append(RollInstructions(
                                                roll_date = actual_roll_date,
                                                from_contract= curr_contract,
                                                to_contract= next_contract,
                                                 ))
            
        return instructions
    
    def stitch_contracts(self, 
                         contracts: list[FuturesContract], 
                         price_map: dict[int, dict[date, FuturesPriceHistory]],
                         roll_instructions: list[RollInstructions],
                         start_date : date,
                         end_date: date) -> list[ContinuousFuturesPriceHistory]:
        continuous_series: list[ContinuousFuturesPriceHistory] = []

        used_dates : dict[date, str] = {}

        for index, contract in enumerate(contracts):
            contract_price = price_map.get(contract.id, {})

            if not contract_price:
                continue

            if index == 0:
                start = start_date
            else:
                start = roll_instructions[index -1].roll_date

            if index < len(roll_instructions):
                end = roll_instructions[index].roll_date
            else:
                end = None

            for price_date in sorted(contract_price):
                if start_date is not None and price_date < start_date:
                    continue
                if end_date is not None and price_date > end_date:
                    continue
                if start is not None and price_date < start:
                    continue
                if end is not None and price_date >= end:
                    continue
                if price_date in used_dates:    
                    prev_contract = used_dates[price_date]
                    raise RuntimeError(f"Date has already been used: {price_date}")
                
                raw_price = contract_price[price_date]

                continuous_series.append(
                    ContinuousFuturesPriceHistory(
                        series=self.series,
                        source_contract=contract,
                        date=raw_price.date,
                        open_price = raw_price.open_price,
                        high_price = raw_price.high_price,
                        low_price = raw_price.low_price,
                        close_price = raw_price.close_price,
                        volume = raw_price.volume,

                        adjustment_val = Decimal("0"),
                        is_roll = True,
                    )
                )

                used_dates[price_date] = contract.contract_code
        
        return sorted(continuous_series, key= lambda x: x.date)