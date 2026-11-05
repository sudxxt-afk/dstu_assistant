from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


# --- Auth ---
class LoginIn(BaseModel):
    password: str


# --- Config ---
class ConfigIn(BaseModel):
    semester_start: dt.date
    semester_end: dt.date
    week1_is_odd: bool
    reminder_minutes: int
    morning_brief_time: str


class ConfigOut(ConfigIn):
    pass


# --- Bells ---
class BellIn(BaseModel):
    pair_number: int
    start_time: str
    end_time: str


# --- Subject ---
class SubjectIn(BaseModel):
    name: str
    teacher: str | None = None
    color: str = "#4f46e5"


class SubjectOut(SubjectIn):
    id: int


# --- Lesson ---
class LessonIn(BaseModel):
    subject_id: int
    type: str = "лекция"
    weekday: int
    pair_number: int
    room: str | None = None
    teacher_override: str | None = None
    parity: str = "every"


class LessonOut(LessonIn):
    id: int


# --- Exception ---
class ExceptionIn(BaseModel):
    date: dt.date
    kind: str  # cancel / move / add
    lesson_id: int | None = None
    subject_id: int | None = None
    type: str | None = None
    new_pair_number: int | None = None
    new_room: str | None = None
    note: str | None = None


class ExceptionOut(ExceptionIn):
    id: int


# --- Task ---
class TaskIn(BaseModel):
    title: str
    subject_id: int | None = None
    due_date: dt.date | None = None
    priority: int = 0


class TaskPatch(BaseModel):
    title: str | None = None
    subject_id: int | None = None
    due_date: dt.date | None = None
    priority: int | None = None
    done: bool | None = None


class TaskOut(TaskIn):
    id: int
    done: bool
    subject_name: str | None = None


# --- Lectures ---
class AttachmentOut(BaseModel):
    id: int
    kind: str  # photo / document
    original_name: str | None
    url: str


class LectureIn(BaseModel):
    subject_id: int
    date: dt.date
    pair_number: int | None = None
    content_md: str = ""


class LecturePatch(BaseModel):
    subject_id: int | None = None
    date: dt.date | None = None
    pair_number: int | None = None
    content_md: str | None = None


class LectureListItem(BaseModel):
    id: int
    subject_id: int
    subject_name: str | None
    date: dt.date
    pair_number: int | None
    preview: str
    attachments: int
    created_at: dt.datetime
    notion_url: str | None = None


class LectureOut(BaseModel):
    id: int
    subject_id: int
    subject_name: str | None
    date: dt.date
    pair_number: int | None
    content_md: str
    created_at: dt.datetime
    attachments: list[AttachmentOut]
    notion_url: str | None = None


# --- Schedule ---
class ResolvedOut(BaseModel):
    subject_id: int
    subject_name: str
    type: str
    pair_number: int
    start_time: str | None
    end_time: str | None
    room: str | None
    teacher: str | None
    status: str
    note: str | None


class DayOut(BaseModel):
    date: dt.date
    weekday: str
    week_number: int
    parity: str
    lessons: list[ResolvedOut]
