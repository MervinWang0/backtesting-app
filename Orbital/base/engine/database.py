# This file creates a connection to a database and creates a session.
# Connection to database -> allows code to manipulate database
# Session -> ongoing changes to the database

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


engine = create_engine("postgresql+psycopg2://postgres:1@localhos:5432/stock_price_db")
Session = sessionmaker(engine)

with Session() as session:
    result = session.execute(text("SELECT 1"))
    print(result.scalar())  # prints 1 if connected successfully