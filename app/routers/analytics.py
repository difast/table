from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, List
from datetime import datetime, timedelta, timezone, date

from app.database import get_db
from app.models import Trade
from app.schemas import TradeOut

router = APIRouter()


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
    except Exception:
        return None


@router.get("/trades", response_model=List[TradeOut])
async def get_trades(
    from_date: Optional[str] = Query(None),
    to_date:   Optional[str] = Query(None),
    instrument: Optional[str] = Query(None),
    direction:  Optional[str] = Query(None),
    strategy:   Optional[str] = Query(None),
    mode:       Optional[str] = Query(None),
    limit: int = Query(200, le=1000),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    filters = []
    if from_date:
        filters.append(Trade.timestamp >= _parse_dt(from_date))
    if to_date:
        filters.append(Trade.timestamp <= _parse_dt(to_date))
    if instrument:
        filters.append(Trade.instrument.ilike(f"%{instrument}%"))
    if direction:
        filters.append(Trade.direction == direction)
    if strategy:
        filters.append(Trade.strategy == strategy)
    if mode:
        filters.append(Trade.mode == mode)

    q = select(Trade).order_by(Trade.timestamp.desc()).offset(offset).limit(limit)
    if filters:
        q = q.where(and_(*filters))
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/pnl")
async def get_pnl(
    period: str = Query("month", regex="^(day|week|month|custom)$"),
    from_date: Optional[str] = Query(None),
    to_date:   Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    if period == "day":
        # Last 30 days, grouped by day
        start = now - timedelta(days=30)
        group_fmt = "%Y-%m-%d"
        label_fmt = "%d.%m"
    elif period == "week":
        start = now - timedelta(weeks=12)
        group_fmt = "%Y-W%W"
        label_fmt = "%Y-W%W"
    elif period == "month":
        start = now - timedelta(days=365)
        group_fmt = "%Y-%m"
        label_fmt = "%m.%Y"
    else:  # custom
        start = _parse_dt(from_date) or (now - timedelta(days=30))
        now   = _parse_dt(to_date) or now
        group_fmt = "%Y-%m-%d"
        label_fmt = "%d.%m"

    q = select(Trade).where(
        and_(Trade.timestamp >= start, Trade.timestamp <= now, Trade.pnl.isnot(None))
    ).order_by(Trade.timestamp)
    result = await db.execute(q)
    trades = result.scalars().all()

    buckets: dict = {}
    for t in trades:
        key = t.timestamp.strftime(group_fmt)
        if key not in buckets:
            buckets[key] = {"label": t.timestamp.strftime(label_fmt), "pnl": 0.0, "trades": 0}
        buckets[key]["pnl"] += t.pnl or 0
        buckets[key]["trades"] += 1

    return {"entries": list(buckets.values()), "total_pnl": sum(b["pnl"] for b in buckets.values())}


@router.get("/summary")
async def get_summary(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start  = now - timedelta(days=7)
    month_start = now - timedelta(days=30)

    async def _count(since):
        r = await db.execute(select(func.count()).where(Trade.timestamp >= since))
        return r.scalar() or 0

    async def _pnl(since):
        r = await db.execute(select(func.sum(Trade.pnl)).where(
            and_(Trade.timestamp >= since, Trade.pnl.isnot(None))
        ))
        return float(r.scalar() or 0)

    total_r = await db.execute(select(func.count(Trade.id)))
    total = total_r.scalar() or 0

    return {
        "total_trades": total,
        "trades_today": await _count(today_start),
        "trades_week":  await _count(week_start),
        "trades_month": await _count(month_start),
        "pnl_today":    await _pnl(today_start),
        "pnl_week":     await _pnl(week_start),
        "pnl_month":    await _pnl(month_start),
        "pnl_total":    await _pnl(datetime.min.replace(tzinfo=timezone.utc)),
    }
