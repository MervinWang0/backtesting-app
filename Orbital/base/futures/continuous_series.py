from dataclasses import dataclass
from datetime import date, timedelta, datetime
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
            print("-----------------------------------------------------------------------\n")
            print("Executing calculate_roll_dates from continuous_series.py\n")
            print(f"This is the len of current trading dates {len(current_trading_dates)}\n")
            print("-----------------------------------------------------------------------\n")
            if len(current_trading_dates) <= roll_days:
                raise RuntimeError(f"Not enough price history for {roll_days}")
            
            roll_index = len(current_trading_dates) -1 - roll_days

            planned_roll_date = current_trading_dates[roll_index]


            def to_date(d):
                if isinstance(d, str):
                    return datetime.datetime.strptime(d, "%Y-%m-%d").date()
                if hasattr(d, 'date'): 
                    return d.date()
                return d 

            curr_dates_norm = {to_date(k) for k in current_prices.keys()}
            next_dates_norm = {to_date(k) for k in next_prices.keys()}

            common_dates_norm = curr_dates_norm & next_dates_norm

            tolerance_start = planned_roll_date - timedelta(days=30) # 30 days is plenty
            tolerance_end = planned_roll_date + timedelta(days=30)

            actual_roll_date = None

            if common_dates_norm:
                valid_common_dates = [d for d in common_dates_norm if tolerance_start <= d <= tolerance_end]
                
                if valid_common_dates:
                    actual_roll_date = min(valid_common_dates, key=lambda d: abs((d - planned_roll_date).days))
                else:
                    actual_roll_date = min(common_dates_norm, key=lambda d: abs((d - planned_roll_date).days))
            else:
                future_next_dates = [d for d in next_dates_norm if d >= planned_roll_date]
                
                if future_next_dates:
                    actual_roll_date = min(future_next_dates)
                    print(f"WARNING: No overlapping data found for {curr_contract.contract_code} -> {next_contract.contract_code}. "
                        f"Falling back to first available date of next contract: {actual_roll_date}")
                else:
                    raise RuntimeError(
                        f"Absolutely no data available for {next_contract.contract_code} "
                        f"on or after {planned_roll_date}"
                    )

            # planned_roll_date = current_trading_dates[roll_index]

            # tolerance_start = planned_roll_date - timedelta(days = 300)
            # tolerance_end = planned_roll_date + timedelta(days = 300)

            # common_dates = sorted(price_date for price_date in (current_prices.keys() & next_prices.keys()) if price_date>=tolerance_start and price_date <= tolerance_end)

            # if not common_dates:
            #     raise RuntimeError(
            #         f"No common rollover date for "
            #         f"{curr_contract.contract_code} -> "
            #         f"{next_contract.contract_code} "
            #         f"on or after {planned_roll_date}"
            #     )

            next_available_dates = sorted(price_date for price_date in next_prices if price_date >= planned_roll_date)

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

        roll_map = {instr.roll_date: instr for instr in roll_instructions}

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

                is_roll_day = price_date in roll_map

                if is_roll_day:
                    roll_instr = roll_map[price_date]
                    from_contract = roll_instr.from_contract
                    to_contract = roll_instr.to_contract

                    from_price_dict = price_map.get(from_contract.id, {})
                    to_price_dict = price_map.get(to_contract.id, {})

                    to_price = to_price_dict.get(price_date)
                    from_price = from_price_dict.get(price_date)
                    if not from_price:
                        past_dates = [day for day in from_price_dict.keys() if day <= price_date]
                        if past_dates:
                            from_price = from_price_dict[max(past_dates)]
                    if not to_price:
                        future_dates = [day for day in to_price_dict.keys() if day >= price_date]
                        if future_dates:
                            to_price = to_price_dict[min(future_dates)]
                
                    roll_from_price = from_price.close_price if from_price else None
                    roll_to_price = to_price.open_price if to_price else None
                else:
                    from_contract = None
                    to_contract = None
                    roll_from_price = None
                    roll_to_price = None

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
                        is_roll = is_roll_day,
                        roll_from_contract = from_contract,
                        roll_to_contract = to_contract,
                        roll_from_price = roll_from_price,
                        roll_to_price = roll_to_price,
                    )
                )

                used_dates[price_date] = contract.contract_code
        
        return sorted(continuous_series, key= lambda x: x.date)