from sqlalchemy import (
    Integer, BigInteger, String, Time, Boolean, 
    ForeignKey, UniqueConstraint
)

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase): 
    pass


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)

    schedules: Mapped[list["Schedule"]] = relationship(back_populates="group")
    users: Mapped[list["TgUser"]] = relationship(back_populates="group")


class Schedule(Base):
    __tablename__ = "schedule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    week: Mapped[str] = mapped_column(String(20))
    weekday: Mapped[str] = mapped_column(String(20))
    pair_num: Mapped[int] = mapped_column(Integer)
    subject: Mapped[str] = mapped_column(String(255))
    start_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    teacher: Mapped[str] = mapped_column(String(255))
    room: Mapped[str] = mapped_column(String(50))
    hash: Mapped[str] = mapped_column(String(255))                  # don't know the hash length yet

    group: Mapped["Group"] = relationship(back_populates="schedules")


class TgUser(Base):
    __tablename__ = "tg_users"

    tg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    notify_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notify_before_min: Mapped[int | None] = mapped_column(Integer, nullable=True)

    group: Mapped["Group"] = relationship(back_populates="users")
    homeworks: Mapped[list["Homework"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    filters: Mapped[list["Filter"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Homework(Base):
    __tablename__ = "homeworks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_user_id: Mapped[int] = mapped_column(ForeignKey("tg_users.tg_id"))
    name: Mapped[str] = mapped_column(String(255))
    file_id: Mapped[str] = mapped_column(String(255))               #Telegram file_id

    user: Mapped["TgUser"] = relationship(back_populates="homeworks")


class Filter(Base):
    __tablename__ = "filters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_user_id: Mapped[int] = mapped_column(ForeignKey("tg_users.tg_id"))
    subject: Mapped[str] = mapped_column(String(255))

    user: Mapped["TgUser"] = relationship(back_populates="filters")

    __table_args__ = (
        UniqueConstraint("tg_user_id", "subject", name="uq_user_subject"),
    )
    