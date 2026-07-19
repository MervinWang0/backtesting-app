from base.engine.data_loader import DatabaseDataLoader


data_loader = DatabaseDataLoader(Queue(), ["TSLA"], data['start_date'],
                             data['end_date'], "STOCK")


    