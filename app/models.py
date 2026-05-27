from sqlalchemy import Column, Integer, String, Float, DateTime, func
from app.database import Base


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=func.now(), index=True)
    instrument = Column(String, index=True)   # ticker / name
    figi = Column(String, index=True)
    direction = Column(String)                # buy | sell
    quantity = Column(Integer)
    price = Column(Float)
    total = Column(Float)
    currency = Column(String, default="RUB")
    strategy = Column(String)
    mode = Column(String)                     # sandbox | live
    status = Column(String, default="executed")
    order_id = Column(String, default="")
    pnl = Column(Float, nullable=True)        # filled when position closes
    signal_value = Column(Float, nullable=True)  # indicator value that triggered
