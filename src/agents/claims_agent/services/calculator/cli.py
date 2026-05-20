"""
Интерактивный консольный интерфейс калькулятора госпошлины.
Запуск: python cli.py
"""
import sys
import os

# Добавляем директорию модуля в путь поиска
sys.path.insert(0, os.path.dirname(__file__))

from agents.claims_agent.services.calculator.fee_calculator import CourtDutyCalculator
from enums import ApplicantType, ClaimType, CourtType, ExemptionType

# ─────────────────────────────────────────────────────────────────────────────
# Меню / справочники
# ─────────────────────────────────────────────────────────────────────────────

COURT_MENU = {
    "1": (CourtType.GENERAL,      "Суд общей юрисдикции / мировой судья / ВС по ГПК/КАС"),
    "2": (CourtType.ARBITRATION,  "Арбитражный суд / ВС по АПК"),
}

CLAIM_MENU = {
    "1":  (ClaimType.PROPERTY,                "Имущественный иск (с ценой иска)"),
    "2":  (ClaimType.NON_PROPERTY,            "Неимущественный / не подлежащий оценке"),
    "3":  (ClaimType.CONTRACT_DISPUTE,        "Договорной спор / признание сделки (без возврата/последствий)"),
    "4":  (ClaimType.COURT_ORDER,             "Заявление о вынесении судебного приказа"),
    "5":  (ClaimType.DIVORCE,                 "Расторжение брака"),
    "6":  (ClaimType.ALIMONY,                 "Взыскание алиментов"),
    "7":  (ClaimType.ADMIN_NORMATIVE,         "Оспаривание нормативного правового акта"),
    "8":  (ClaimType.ADMIN_NON_NORMATIVE,     "Оспаривание ненормативного акта / действий (бездействия)"),
    "9":  (ClaimType.SPECIAL_PROCEEDING,      "Особое производство (только общ. юрисдикция)"),
    "10": (ClaimType.FACT_ESTABLISHMENT,      "Установление фактов (только арбитраж)"),
    "11": (ClaimType.INTERIM_MEASURES,        "Обеспечение иска / замена / отмена меры"),
    "12": (ClaimType.APPEAL,                  "Апелляционная жалоба / частная / касс. на приказ"),
    "13": (ClaimType.CASSATION,               "Кассационная жалоба"),
    "14": (ClaimType.SUPREME_CASSATION,       "Кассационная/надзорная жалоба в Верховный Суд РФ"),
    "15": (ClaimType.BANKRUPTCY,              "Заявление о банкротстве (арбитраж)"),
    "16": (ClaimType.BANKRUPTCY_DISPUTE,      "Обособленный спор в деле о банкротстве"),
    "17": (ClaimType.ENFORCEMENT_FOREIGN,     "Исполнение решения третейского / иностранного суда"),
    "18": (ClaimType.CANCEL_ARBITRATION,      "Отмена решения третейского суда"),
    "19": (ClaimType.REVIEW_NEW_CIRCUMSTANCES,"Пересмотр по новым / вновь открывшимся обстоятельствам"),
    "20": (ClaimType.DUPLICATE_WRIT,          "Дубликат исп. листа / пересмотр заочного решения"),
    "21": (ClaimType.EXECUTION_ISSUES,        "Отсрочка/рассрочка/разъяснение суд. акта (общ. юрисдикция)"),
    "22": (ClaimType.SUCCESSION,              "Правопреемство"),
    "23": (ClaimType.COMPENSATION_DELAY,      "Компенсация за нарушение разумного срока"),
    "24": (ClaimType.COMPENSATION_DETENTION,  "Компенсация за условия содержания (общ. юрисдикция)"),
    "25": (ClaimType.IP_NORMATIVE,            "Оспаривание НПА в сфере интеллектуальной собственности"),
    "26": (ClaimType.IP_CLARIFICATION,        "Оспаривание разъяснительного акта в сфере ИС (арбитраж)"),
}

EXEMPTION_MENU = {
    "0": (ExemptionType.NONE,              "Нет льгот"),
    "1": (ExemptionType.ALIMONY_PLAINTIFF, "Истец по алиментам"),
    "2": (ExemptionType.LABOR_DISPUTE,     "Работник — трудовой спор"),
    "3": (ExemptionType.CONSUMER_PROTECTION, "Защита прав потребителей"),
    "4": (ExemptionType.HEALTH_DAMAGE,     "Вред здоровью / смерть кормильца"),
    "5": (ExemptionType.CRIME_VICTIM,      "Реабилитация (уголовное дело)"),
    "6": (ExemptionType.DISABILITY_1_2,    "Инвалид I или II группы"),
    "7": (ExemptionType.PENSION_SOCIAL,    "Пенсионер / получатель соц. пособий (соц. дела)"),
    "8": (ExemptionType.PROSECUTOR,        "Прокурор / госорган (публичные интересы)"),
    "9": (ExemptionType.BANKRUPTCY_DEBTOR, "Должник — сам подаёт на банкротство"),
    "10": (ExemptionType.VETERAN,          "Ветеран (по делам, связанным с защитой прав ветерана)"),
}

# ─────────────────────────────────────────────────────────────────────────────
# Утилиты ввода
# ─────────────────────────────────────────────────────────────────────────────

def _banner() -> None:
    print("\n" + "═" * 60)
    print("   КАЛЬКУЛЯТОР ГОСУДАРСТВЕННОЙ ПОШЛИНЫ")
    print("   (НК РФ ст. 333.19, 333.21, 333.36 в ред. ФЗ от 08.08.2024 № 259-ФЗ)")
    print("═" * 60)


def _choose(prompt: str, menu: dict) -> str:
    print(f"\n{prompt}")
    for k, (_, label) in menu.items():
        print(f"  {k:>3}. {label}")
    while True:
        choice = input("Ваш выбор: ").strip()
        if choice in menu:
            return choice
        print("  ⚠  Неверный выбор. Попробуйте ещё раз.")


def _ask_amount(prompt: str, allow_zero: bool = False) -> float:
    while True:
        raw = input(prompt).strip().replace(" ", "").replace(",", ".")
        try:
            val = float(raw)
            if val < 0:
                raise ValueError
            if not allow_zero and val == 0:
                print("  ⚠  Введите сумму больше нуля.")
                continue
            return val
        except ValueError:
            print("  ⚠  Введите число (например: 350000 или 1500000.50).")


def _ask_yes_no(prompt: str) -> bool:
    while True:
        ans = input(f"{prompt} (д/н): ").strip().lower()
        if ans in ("д", "да", "y", "yes", "1"):
            return True
        if ans in ("н", "нет", "n", "no", "0"):
            return False
        print("  ⚠  Введите 'д' или 'н'.")


# ─────────────────────────────────────────────────────────────────────────────
# Главный диалог
# ─────────────────────────────────────────────────────────────────────────────

def run() -> None:
    _banner()

    # 1. Тип суда
    court_choice = _choose("1. Выберите тип суда:", COURT_MENU)
    court_type, court_label = COURT_MENU[court_choice]

    # 2. Тип иска / заявления
    claim_choice = _choose("2. Выберите вид иска / заявления:", CLAIM_MENU)
    claim_type, claim_label = CLAIM_MENU[claim_choice]

    # 3. Заявитель
    applicant_choice = _choose(
        "3. Кто заявитель?",
        {
            "1": (ApplicantType.INDIVIDUAL,   "Физическое лицо"),
            "2": (ApplicantType.ORGANIZATION, "Организация / ИП"),
        },
    )
    applicant_type = ApplicantType.INDIVIDUAL if applicant_choice == "1" else ApplicantType.ORGANIZATION

    # 4. Цена иска (если нужна)
    claim_amount = 0.0
    NEEDS_AMOUNT = {
        ClaimType.PROPERTY,
        ClaimType.COURT_ORDER,
        ClaimType.ENFORCEMENT_FOREIGN,
        ClaimType.CANCEL_ARBITRATION,
        ClaimType.BANKRUPTCY_DISPUTE,
    }
    if claim_type in NEEDS_AMOUNT:
        claim_amount = _ask_amount("\n4. Введите цену иска / сумму требования (₽): ")

    # 5. Льготы
    exemption_choice = _choose("5. Есть ли основания для льготы?", EXEMPTION_MENU)
    exemption, exemption_label = EXEMPTION_MENU[exemption_choice]

    # 6. Доп. параметры
    consumer_claim_amount: float | None = None
    both_alimony = False
    is_debtor_bankruptcy = False

    if exemption == ExemptionType.CONSUMER_PROTECTION:
        consumer_claim_amount = _ask_amount(
            "\n5а. Цена потребительского иска (₽): "
        )

    if claim_type == ClaimType.ALIMONY:
        both_alimony = _ask_yes_no(
            "\n6. Взыскиваются ли алименты одновременно на детей И на самого истца?"
        )

    if claim_type == ClaimType.BANKRUPTCY and applicant_type == ApplicantType.INDIVIDUAL:
        is_debtor_bankruptcy = _ask_yes_no(
            "\n6. Должник сам подаёт заявление о собственном банкротстве?"
        )
    elif claim_type == ClaimType.BANKRUPTCY and applicant_type == ApplicantType.ORGANIZATION:
        is_debtor_bankruptcy = _ask_yes_no(
            "\n6. Организация-должник сама подаёт заявление о своём банкротстве?"
        )

    # 7. Расчёт
    calc = CourtDutyCalculator(
        court_type=court_type,
        claim_type=claim_type,
        applicant_type=applicant_type,
        claim_amount=claim_amount,
        exemption=exemption,
        consumer_claim_amount=consumer_claim_amount,
        both_alimony=both_alimony,
        is_debtor_bankruptcy=is_debtor_bankruptcy,
    )

    result = calc.calculate()

    # 8. Вывод
    print("\n")
    print(f"  Суд:      {court_label}")
    print(f"  Иск:      {claim_label}")
    print(f"  Заявитель: {'физ. лицо' if applicant_type == ApplicantType.INDIVIDUAL else 'организация'}")
    if claim_amount:
        print(f"  Сумма:    {claim_amount:,.2f} ₽".replace(",", " "))
    if exemption != ExemptionType.NONE:
        print(f"  Льгота:   {exemption_label}")
    print()
    print(result)

    # 9. Ещё расчёт?
    print()
    if _ask_yes_no("Рассчитать ещё раз?"):
        run()
    else:
        print("\nДо свидания!")


# ─────────────────────────────────────────────────────────────────────────────
# Точка входа
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем.")
