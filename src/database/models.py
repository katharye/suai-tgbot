from sqlalchemy import (
    Integer, BigInteger, String, Time, Boolean, 
    ForeignKey, UniqueConstraint
)

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    """Common parent class for all models. Necessary for Alembic"""
    pass


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)

    schedules: Mapped[list["Schedule"]] = relationship(back_populates="group")
    users: Mapped[list["VkUser"]] = relationship(back_populates="group")


class Schedule(Base):
    __tablename__ = "schedule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    week: Mapped[str] = mapped_column(String(20))
    weekday: Mapped[str] = mapped_column(String(20))
    class_num: Mapped[int] = mapped_column(Integer)
    subject: Mapped[str] = mapped_column(String(255))
    start_time: Mapped[int] = mapped_column(Integer)  # seconds from start of day
    teacher: Mapped[str] = mapped_column(String(255))
    room: Mapped[str] = mapped_column(String(50))
    lesson_type: Mapped[str] = mapped_column(String(10), nullable=True)  # л, пр, лр
    hash: Mapped[str] = mapped_column(String(255))

    group: Mapped["Group"] = relationship(back_populates="schedules")


class VkUser(Base):
    __tablename__ = "vk_users"

    vk_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    notify_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_time: Mapped[int] = mapped_column(Integer, nullable=True)  # seconds from start of day
    notify_before_min: Mapped[int] = mapped_column(Integer, default=15)

    group: Mapped["Group"] = relationship(back_populates="users")
    homeworks: Mapped[list["Homework"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    filters: Mapped[list["Filter"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    hidden_subjects: Mapped[list["HiddenSubject"]] = relationship(
        cascade="all, delete-orphan"
    )


class Homework(Base):
    __tablename__ = "homeworks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vk_user_id: Mapped[int] = mapped_column(ForeignKey("vk_users.vk_id"))
    name: Mapped[str] = mapped_column(String(255))
    file_id: Mapped[str] = mapped_column(String(255), nullable=True)  # VK attachment-строка (doc<owner>_<id>)
    description: Mapped[str] = mapped_column(String(2000), nullable=True)  # текст домашки
    remind_time: Mapped[int] = mapped_column(Integer, nullable=True)  # timestamp для напоминания

    user: Mapped["VkUser"] = relationship(back_populates="homeworks")


class Filter(Base):
    __tablename__ = "filters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vk_user_id: Mapped[int] = mapped_column(ForeignKey("vk_users.vk_id"))
    subject: Mapped[str] = mapped_column(String(255))

    user: Mapped["VkUser"] = relationship(back_populates="filters")

    __table_args__ = (
        UniqueConstraint("vk_user_id", "subject", name="uq_user_subject"),
    )


class ClassTime(Base):
    __tablename__ = "class_times"

    class_num: Mapped[int] = mapped_column(Integer, primary_key=True)
    start_time: Mapped[int] = mapped_column(Integer)  # seconds from start of day


class HiddenSubject(Base):
    __tablename__ = "hidden_subjects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vk_user_id: Mapped[int] = mapped_column(ForeignKey("vk_users.vk_id"))
    subject: Mapped[str] = mapped_column(String(255))
    weekday: Mapped[str] = mapped_column(String(20))

    __table_args__ = (
        UniqueConstraint("vk_user_id", "subject", "weekday", name="uq_user_subject_weekday"),
    )
    