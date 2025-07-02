from enum import Enum


class ProjectType(Enum):
    PLANNED = "плановый"
    CLIENT = "клиентский"
    FOR_CUSTOM = "для кастомов"
    FOR_NONPROJECT = "для непроектных"


class Status(Enum):
    IN_PROGRESS = "в работе"
    COMPLETED = "завершён"
    ON_HOLD = "на паузе"
    CANCELLED = "отменен"


class Department(Enum):
    FONT = "шрифтовой"
    TECHNICAL = "технический"
    GRAPHIC = "графический"
    CONTENT = "контентный"


class Stage(Enum):
    PREPARATION = "подготовка"
    DRAWING_STRAIGHT = "отрисовка прямые"
    DRAWING_ITALIC = "отрисовка италики"
    DRAWING_CAPITAL = "отрисовка капитель"
    TECHNICAL = "техничка"
    FORMATTING = "оформление"


class WeekDay(Enum):
    MONDAY = "понедельник"
    TUESDAY = "вторник"
    WEDNESDAY = "среда"
    THURSDAY = "четверг"
    FRIDAY = "пятница"
    SATURDAY = "суббота"
    SUNDAY = "воскресенье"


class TaskStatus(Enum):
    IN_PROGRESS = "в процессе"
    COMPLETED = "готова"
