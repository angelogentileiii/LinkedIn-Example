from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Index,
    Date,
    Numeric
)

from .base import Base

class SECFTDInfoTable(Base):
    __tablename__ = "sec_ftd_infotable"

    ID = Column(Integer, autoincrement=True, primary_key=True, nullable=False)
    SETTLE_DATE = Column(Date, default=None)
    CUSIP = Column(String(15), default=None)
    SYMBOL = Column(String(15), default=None)
    COMP_NAME = Column(String(50), default=None)
    QUANTITY = Column(BigInteger, default=None)
    PRICE = Column(Numeric(10,2), default = None)
    UPDATE_REVISION = Column(String(50), default = None)

    __table_args__ = (
        Index('idx_sec_ftd_cusip', 'CUSIP', 'SYMBOL'),
        Index('idx_sec_ftd_compname', 'COMP_NAME', 'SYMBOL')
    )