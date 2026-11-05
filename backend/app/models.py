from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

# --- Справочные значения (хранятся строками для простоты) ---
LESSON_TYPES = ("лекция", "практика", "лаба", "семинар")
PARITY = ("every", "odd", "even")  # каждую / нечётная / чётная
EXCEPTION_KINDS = ("cancel", "move", "add")


class Config(Base):
    """Единственная строка настроек (id=1)."""

    __tablename__ = "config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    semester_start: Mapped[dt.date] = mapped_column(Date)
    semester_end: Mapped[dt.date] = mapped_column(Date)
    week1_is_odd: Mapped[bool] = mapped_column(Boolean, default=True)
    reminder_minutes: Mapped[int] = mapped_column(Integer, default=10)
    morning_brief_time: Mapped[str] = mapped_column(String(5), default="07:30")


class BellSchedule(Base):
    """Расписание звонков: номер пары -> время."""

    __tablename__ = "bell_schedule"

    pair_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    start_time: Mapped[str] = mapped_column(String(5))  # "HH:MM"
    end_time: Mapped[str] = mapped_column(String(5))


class Subject(Base):
    __tablename__ = "subject"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    teacher: Mapped[str | None] = mapped_column(String(200), nullable=True)
    color: Mapped[str] = mapped_column(String(9), default="#4f46e5")

    lessons: Mapped[list["Lesson"]] = relationship(back_populates="subject")


class Lesson(Base):
    """Шаблон повторяющейся пары."""

    __tablename__ = "lesson"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subject.id"))
    type: Mapped[str] = mapped_column(String(20), default="лекция")
    weekday: Mapped[int] = mapped_column(Integer)  # 1=Пн ... 7=Вс (ISO)
    pair_number: Mapped[int] = mapped_column(Integer)
    room: Mapped[str | None] = mapped_column(String(50), nullable=True)
    teacher_override: Mapped[str | None] = mapped_column(String(200), nullable=True)
    parity: Mapped[str] = mapped_column(String(10), default="every")

    subject: Mapped["Subject"] = relationship(back_populates="lessons")


class Exception(Base):
    """Исключение на конкретную дату: отмена / перенос / разовая пара."""

    __tablename__ = "exception"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[dt.date] = mapped_column(Date)
    kind: Mapped[str] = mapped_column(String(10))  # cancel / move / add
    lesson_id: Mapped[int | None] = mapped_column(
        ForeignKey("lesson.id"), nullable=True
    )
    # Для move: новые значения. Для add: субъект/тип/пара/аудитория.
    subject_id: Mapped[int | None] = mapped_column(
        ForeignKey("subject.id"), nullable=True
    )
    type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_pair_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_room: Mapped[str | None] = mapped_column(String(50), nullable=True)
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)


class LectureNote(Base):
    __tablename__ = "lecture_note"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subject.id"))
    date: Mapped[dt.date] = mapped_column(Date)
    pair_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_md: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=dt.datetime.utcnow
    )

    subject: Mapped["Subject"] = relationship()
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="note", cascade="all, delete-orphan"
    )


class Attachment(Base):
    __tablename__ = "attachment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    note_id: Mapped[int] = mapped_column(ForeignKey("lecture_note.id"))
    kind: Mapped[str] = mapped_column(String(20))  # photo / document
    file_path: Mapped[str] = mapped_column(String(500))
    original_name: Mapped[str | None] = mapped_column(String(300), nullable=True)

    note: Mapped["LectureNote"] = relationship(back_populates="attachments")


class Task(Base):
    __tablename__ = "task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int | None] = mapped_column(
        ForeignKey("subject.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(300))
    due_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[int] = mapped_column(Integer, default=0)  # 0 — обычная, 1 — важная
    remind_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=dt.datetime.utcnow
    )

    subject: Mapped["Subject | None"] = relationship()
