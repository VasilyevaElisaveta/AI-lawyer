"""
Ядро расчёта госпошлины.

Все ставки актуальны по состоянию на дату вступления в силу
Федерального закона от 08.08.2024 № 259-ФЗ.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .enums import (
    ApplicantType,
    ClaimType,
    CourtType,
    ExemptionType,
)


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные функции: шкалы
# ─────────────────────────────────────────────────────────────────────────────

def _calc_general_property(claim_amount: float) -> float:
    """
    Ст. 333.19 НК РФ, пп. 1 п. 1.
    Суд общей юрисдикции, имущественный иск.
    """
    a = claim_amount
    if a <= 0:
        return 4_000.0
    if a <= 100_000:
        return 4_000.0
    if a <= 300_000:
        return 4_000 + 0.03 * (a - 100_000)
    if a <= 500_000:
        return 10_000 + 0.025 * (a - 300_000)
    if a <= 1_000_000:
        return 15_000 + 0.02 * (a - 500_000)
    if a <= 3_000_000:
        return 25_000 + 0.01 * (a - 1_000_000)
    if a <= 8_000_000:
        return 45_000 + 0.007 * (a - 3_000_000)
    if a <= 24_000_000:
        return 80_000 + 0.0035 * (a - 8_000_000)
    if a <= 50_000_000:
        return 136_000 + 0.003 * (a - 24_000_000)
    if a <= 100_000_000:
        return 214_000 + 0.002 * (a - 50_000_000)
    # свыше 100 млн, но не более 900 000
    raw = 314_000 + 0.0015 * (a - 100_000_000)
    return min(raw, 900_000.0)


def _calc_arbitration_property(claim_amount: float) -> float:
    """
    Ст. 333.21 НК РФ, пп. 1 п. 1.
    Арбитражный суд, имущественный иск.
    """
    a = claim_amount
    if a <= 0:
        return 10_000.0
    if a <= 100_000:
        return 10_000.0
    if a <= 1_000_000:
        return 10_000 + 0.05 * (a - 100_000)
    if a <= 10_000_000:
        return 55_000 + 0.03 * (a - 1_000_000)
    if a <= 50_000_000:
        return 325_000 + 0.01 * (a - 10_000_000)
    # свыше 50 млн: 725 000 + 0,5% от суммы сверх 50 млн, но не более 10 000 000
    # Кэп 10 000 000 достигается при: 725 000 + 0.005*(x-50 000 000) = 10 000 000
    # → x = 50 000 000 + (10 000 000 - 725 000) / 0.005 = 50 000 000 + 1 855 000 000
    # т.е. при любой разумной сумме иска кэп не достигается,
    # но формально ограничение есть
    raw = 725_000 + 0.005 * (a - 50_000_000)
    return min(raw, 10_000_000.0)


# ─────────────────────────────────────────────────────────────────────────────
# Датакласс результата
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DutyResult:
    """Результат расчёта госпошлины."""
    amount: float                  # Итоговая сумма к уплате (руб.)
    base_amount: float             # Сумма до применения льготы
    is_exempt: bool                # Полное освобождение
    exemption_details: str         # Описание льготы / основания
    calculation_details: str       # Подробный расчёт
    warnings: list[str] = field(default_factory=list)  # Предупреждения

    def __str__(self) -> str:
        lines = [
            "═" * 60,
            "  РЕЗУЛЬТАТ РАСЧЁТА ГОСПОШЛИНЫ",
            "═" * 60,
        ]
        if self.is_exempt:
            lines.append(f"  ✅ ОСВОБОЖДЕНИЕ ОТ ГОСПОШЛИНЫ")
            lines.append(f"  Основание: {self.exemption_details}")
            lines.append(f"  К уплате: 0 ₽")
        else:
            if self.exemption_details:
                lines.append(f"  ℹ️  Льгота: {self.exemption_details}")
            lines.append(f"  К уплате: {self.amount:,.2f} ₽".replace(",", " "))
        lines.append("")
        lines.append("  📋 Расчёт:")
        for ln in self.calculation_details.splitlines():
            lines.append(f"  {ln}")
        if self.warnings:
            lines.append("")
            lines.append("  ⚠️  Внимание:")
            for w in self.warnings:
                lines.append(f"  • {w}")
        lines.append("═" * 60)
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Главный класс
# ─────────────────────────────────────────────────────────────────────────────

class CourtDutyCalculator:
    """
    Калькулятор государственной пошлины.

    Параметры
    ---------
    court_type : CourtType
        Вид суда (общей юрисдикции или арбитражный).
    claim_type : ClaimType
        Вид заявления / иска.
    applicant_type : ApplicantType
        Физическое лицо или организация.
    claim_amount : float, optional
        Цена иска в рублях (для имущественных исков).
    exemption : ExemptionType, optional
        Основание для льготы (ст. 333.36 НК РФ).
    consumer_claim_amount : float, optional
        Цена иска для потребительских споров (льгота действует
        только до 1 000 000 ₽; свыше — пошлина с превышения).
    both_alimony : bool, optional
        Для дел об алиментах: если суд взыскивает алименты
        и на детей, и на самого истца — пошлина удваивается.
        (Актуально, когда ответчик платит пошлину.)
    is_debtor_bankruptcy : bool, optional
        Должник сам подаёт заявление о банкротстве — пошлина
        не взимается.
    """

    MAX_GENERAL = 900_000.0
    MAX_ARBITRATION = 10_000_000.0

    def __init__(
        self,
        court_type: CourtType,
        claim_type: ClaimType,
        applicant_type: ApplicantType = ApplicantType.INDIVIDUAL,
        claim_amount: float = 0.0,
        exemption: ExemptionType = ExemptionType.NONE,
        consumer_claim_amount: Optional[float] = None,
        both_alimony: bool = False,
        is_debtor_bankruptcy: bool = False,
    ) -> None:
        self.court_type = court_type
        self.claim_type = claim_type
        self.applicant_type = applicant_type
        self.claim_amount = max(0.0, float(claim_amount))
        self.exemption = exemption
        self.consumer_claim_amount = consumer_claim_amount
        self.both_alimony = both_alimony
        self.is_debtor_bankruptcy = is_debtor_bankruptcy

    # ── Публичный метод ──────────────────────────────────────────────────────

    def calculate(self) -> DutyResult:
        """Рассчитать госпошлину и вернуть детальный результат."""
        warnings: list[str] = []

        # 1. Специальные случаи полного освобождения
        exempt_result = self._check_full_exemption(warnings)
        if exempt_result is not None:
            return exempt_result

        # 2. Основной расчёт
        base, details = self._compute_base(warnings)

        # 3. Льготы, уменьшающие пошлину (но не до нуля)
        final, exemption_note = self._apply_partial_exemption(base, details, warnings)

        return DutyResult(
            amount=round(final, 2),
            base_amount=round(base, 2),
            is_exempt=False,
            exemption_details=exemption_note,
            calculation_details=details,
            warnings=warnings,
        )

    # ── Полное освобождение ──────────────────────────────────────────────────

    def _check_full_exemption(self, warnings: list[str]) -> Optional[DutyResult]:
        """Проверить, полностью ли освобождён заявитель от пошлины."""

        # Должник-банкрот подаёт сам на себя
        if (
            self.claim_type == ClaimType.BANKRUPTCY
            and self.is_debtor_bankruptcy
        ):
            return DutyResult(
                amount=0.0,
                base_amount=0.0,
                is_exempt=True,
                exemption_details=(
                    "Должник, самостоятельно подающий заявление о банкротстве, "
                    "освобождён от уплаты госпошлины (ст. 333.21 НК РФ, пп. 8 п. 1)."
                ),
                calculation_details="Пошлина не взимается.",
                warnings=warnings,
            )

        # Алименты — истец
        if (
            self.exemption == ExemptionType.ALIMONY_PLAINTIFF
            and self.claim_type == ClaimType.ALIMONY
        ):
            warnings.append(
                "Пошлину (150 ₽ или 300 ₽) суд взыщет с ответчика."
            )
            return DutyResult(
                amount=0.0,
                base_amount=150.0,
                is_exempt=True,
                exemption_details=(
                    "Истцы по алиментам освобождены от уплаты пошлины "
                    "(ст. 333.36 НК РФ). Пошлина взыскивается с ответчика."
                ),
                calculation_details=(
                    f"Базовая пошлина по алиментам: 150 ₽"
                    + (" × 2 = 300 ₽ (алименты на детей + истца)" if self.both_alimony else "")
                    + "\nК уплате истцом: 0 ₽"
                ),
                warnings=warnings,
            )

        # Трудовые споры
        if self.exemption == ExemptionType.LABOR_DISPUTE:
            return DutyResult(
                amount=0.0,
                base_amount=0.0,
                is_exempt=True,
                exemption_details=(
                    "Работники по трудовым спорам (зарплата, восстановление, "
                    "увольнение и т.д.) освобождены от госпошлины "
                    "(ст. 333.36 НК РФ)."
                ),
                calculation_details="Пошлина не взимается.",
                warnings=warnings,
            )

        # Вред здоровью / смерть кормильца / реабилитация
        if self.exemption in (
            ExemptionType.HEALTH_DAMAGE,
            ExemptionType.CRIME_VICTIM,
        ):
            return DutyResult(
                amount=0.0,
                base_amount=0.0,
                is_exempt=True,
                exemption_details=(
                    "Иски о возмещении вреда здоровью / смерти кормильца / "
                    "по реабилитации освобождены от госпошлины "
                    "(ст. 333.36 НК РФ)."
                ),
                calculation_details="Пошлина не взимается.",
                warnings=warnings,
            )

        # Пенсионеры / получатели соц. пособий — по соц. делам
        if self.exemption == ExemptionType.PENSION_SOCIAL:
            return DutyResult(
                amount=0.0,
                base_amount=0.0,
                is_exempt=True,
                exemption_details=(
                    "Пенсионеры и получатели социальных пособий освобождены от "
                    "пошлины по делам, связанным с защитой их социальных прав "
                    "(ст. 333.36 НК РФ)."
                ),
                calculation_details="Пошлина не взимается.",
                warnings=warnings,
            )

        # Прокурор / госорган
        if self.exemption == ExemptionType.PROSECUTOR:
            return DutyResult(
                amount=0.0,
                base_amount=0.0,
                is_exempt=True,
                exemption_details=(
                    "Прокуроры и государственные органы, обращающиеся в суд "
                    "в защиту публичных интересов, освобождены от пошлины "
                    "(ст. 333.36 НК РФ)."
                ),
                calculation_details="Пошлина не взимается.",
                warnings=warnings,
            )

        # Ветераны (по отдельным делам)
        if self.exemption == ExemptionType.VETERAN:
            warnings.append(
                "Льгота ветеранам действует только по делам, связанным с "
                "защитой их прав как ветеранов. Уточните применимость."
            )
            return DutyResult(
                amount=0.0,
                base_amount=0.0,
                is_exempt=True,
                exemption_details=(
                    "Ветераны освобождены от госпошлины по делам, "
                    "связанным с защитой их прав (ст. 333.36 НК РФ)."
                ),
                calculation_details="Пошлина не взимается.",
                warnings=warnings,
            )

        return None  # освобождения нет

    # ── Основной расчёт ──────────────────────────────────────────────────────

    def _compute_base(self, warnings: list[str]) -> tuple[float, str]:
        """Рассчитать базовую пошлину без льгот."""
        ct = self.claim_type
        cv = self.court_type
        at = self.applicant_type
        is_ind = at == ApplicantType.INDIVIDUAL
        is_arb = cv == CourtType.ARBITRATION

        # ── ИМУЩЕСТВЕННЫЙ ИСК ────────────────────────────────────────────────
        if ct == ClaimType.PROPERTY:
            if is_arb:
                base = _calc_arbitration_property(self.claim_amount)
                detail = (
                    f"Арбитражный суд, имущественный иск.\n"
                    f"Цена иска: {self.claim_amount:,.2f} ₽\n"
                    f"Пошлина (ст. 333.21 НК РФ, пп. 1): {base:,.2f} ₽"
                ).replace(",", " ")
            else:
                base = _calc_general_property(self.claim_amount)
                detail = (
                    f"Суд общей юрисдикции, имущественный иск.\n"
                    f"Цена иска: {self.claim_amount:,.2f} ₽\n"
                    f"Пошлина (ст. 333.19 НК РФ, пп. 1): {base:,.2f} ₽"
                ).replace(",", " ")
            return base, detail

        # ── СУДЕБНЫЙ ПРИКАЗ ───────────────────────────────────────────────────
        if ct == ClaimType.COURT_ORDER:
            if is_arb:
                base_prop = _calc_arbitration_property(self.claim_amount)
                base = max(base_prop * 0.5, 8_000.0)
                detail = (
                    f"Арбитражный суд, судебный приказ.\n"
                    f"Цена требования: {self.claim_amount:,.2f} ₽\n"
                    f"Базовая пошлина (50% от {base_prop:,.2f} ₽) = {base_prop*0.5:,.2f} ₽\n"
                    f"Минимум: 8 000 ₽\n"
                    f"К уплате (ст. 333.21 НК РФ, пп. 3): {base:,.2f} ₽"
                ).replace(",", " ")
            else:
                base_prop = _calc_general_property(self.claim_amount)
                base = base_prop * 0.5
                detail = (
                    f"Суд общей юрисдикции, судебный приказ.\n"
                    f"Цена требования: {self.claim_amount:,.2f} ₽\n"
                    f"Пошлина = 50% от {base_prop:,.2f} ₽ = {base:,.2f} ₽\n"
                    f"(ст. 333.19 НК РФ, пп. 2)"
                ).replace(",", " ")
            return base, detail

        # ── НЕИМУЩЕСТВЕННЫЙ / НЕ ПОДЛЕЖАЩИЙ ОЦЕНКЕ ──────────────────────────
        if ct == ClaimType.NON_PROPERTY:
            if is_arb:
                base = 50_000.0 if not is_ind else 15_000.0
                detail = (
                    f"Арбитражный суд, неимущественный иск.\n"
                    f"Заявитель: {'физ. лицо' if is_ind else 'организация'}.\n"
                    f"Пошлина (ст. 333.21 НК РФ, пп. 4): {base:,.2f} ₽"
                ).replace(",", " ")
            else:
                base = 3_000.0 if is_ind else 20_000.0
                detail = (
                    f"Суд общей юрисдикции, неимущественный иск.\n"
                    f"Заявитель: {'физ. лицо' if is_ind else 'организация'}.\n"
                    f"Пошлина (ст. 333.19 НК РФ, пп. 3): {base:,.2f} ₽"
                ).replace(",", " ")
            return base, detail

        # ── ДОГОВОРНОЙ СПОР (БЕЗ ВОЗВРАТА / БЕЗ ПОСЛЕДСТВИЙ) ────────────────
        if ct == ClaimType.CONTRACT_DISPUTE:
            if is_arb:
                base = 50_000.0 if not is_ind else 15_000.0
                detail = (
                    f"Арбитражный суд, договорной спор / признание сделки.\n"
                    f"Заявитель: {'физ. лицо' if is_ind else 'организация'}.\n"
                    f"Пошлина (ст. 333.21 НК РФ, пп. 2): {base:,.2f} ₽"
                ).replace(",", " ")
            else:
                base = 3_000.0 if is_ind else 20_000.0
                detail = (
                    f"Суд общей юрисдикции, договорной спор / признание сделки.\n"
                    f"Заявитель: {'физ. лицо' if is_ind else 'организация'}.\n"
                    f"Пошлина (ст. 333.19 НК РФ, пп. 4): {base:,.2f} ₽"
                ).replace(",", " ")
            return base, detail

        # ── РАСТОРЖЕНИЕ БРАКА ─────────────────────────────────────────────────
        if ct == ClaimType.DIVORCE:
            if is_arb:
                warnings.append(
                    "Иски о расторжении брака рассматриваются судами общей "
                    "юрисдикции, а не арбитражными судами."
                )
            base = 5_000.0
            detail = (
                f"Иск о расторжении брака.\n"
                f"Пошлина (ст. 333.19 НК РФ, пп. 5): {base:,.2f} ₽"
            ).replace(",", " ")
            return base, detail

        # ── АЛИМЕНТЫ ──────────────────────────────────────────────────────────
        if ct == ClaimType.ALIMONY:
            base = 300.0 if self.both_alimony else 150.0
            detail = (
                f"Заявление о взыскании алиментов.\n"
                + (
                    "Алименты на детей + на истца: 150 ₽ × 2 = 300 ₽\n"
                    if self.both_alimony
                    else "Пошлина: 150 ₽\n"
                )
                + "(ст. 333.19 НК РФ, пп. 16)\n"
                + "Примечание: пошлина обычно взыскивается с ответчика."
            )
            return base, detail

        # ── АДМИНИСТРАТИВНЫЕ ─────────────────────────────────────────────────
        if ct == ClaimType.ADMIN_NORMATIVE:
            base = 4_000.0 if is_ind else 20_000.0
            detail = (
                f"Оспаривание нормативных правовых актов.\n"
                f"Заявитель: {'физ. лицо' if is_ind else 'организация'}.\n"
                f"Пошлина (ст. 333.19 НК РФ, пп. 6): {base:,.2f} ₽"
            ).replace(",", " ")
            return base, detail

        if ct == ClaimType.ADMIN_NON_NORMATIVE:
            base = 3_000.0 if is_ind else 15_000.0
            detail = (
                f"Оспаривание ненормативных актов / действий (бездействия).\n"
                f"Заявитель: {'физ. лицо' if is_ind else 'организация'}.\n"
                f"Пошлина (ст. 333.19 НК РФ, пп. 7 / ст. 333.21 НК РФ, пп. 7): {base:,.2f} ₽"
            ).replace(",", " ")
            # арбитраж: 10 000 / 50 000
            if is_arb:
                base = 50_000.0 if not is_ind else 10_000.0
                detail = (
                    f"Арбитражный суд, оспаривание ненормативных актов.\n"
                    f"Заявитель: {'физ. лицо' if is_ind else 'организация'}.\n"
                    f"Пошлина (ст. 333.21 НК РФ, пп. 7): {base:,.2f} ₽"
                ).replace(",", " ")
            return base, detail

        # ── ОСОБОЕ ПРОИЗВОДСТВО (общая юрисдикция) ───────────────────────────
        if ct == ClaimType.SPECIAL_PROCEEDING:
            base = 3_000.0
            detail = (
                f"Заявление по делам особого производства.\n"
                f"Пошлина (ст. 333.19 НК РФ, пп. 8): {base:,.2f} ₽"
            ).replace(",", " ")
            return base, detail

        # ── УСТАНОВЛЕНИЕ ФАКТОВ (арбитраж) ───────────────────────────────────
        if ct == ClaimType.FACT_ESTABLISHMENT:
            base = 30_000.0
            detail = (
                f"Арбитражный суд, установление фактов.\n"
                f"Пошлина (ст. 333.21 НК РФ, пп. 10): {base:,.2f} ₽"
            ).replace(",", " ")
            return base, detail

        # ── ОБЕСПЕЧИТЕЛЬНЫЕ МЕРЫ ─────────────────────────────────────────────
        if ct == ClaimType.INTERIM_MEASURES:
            if is_arb:
                base = 30_000.0
                detail = (
                    f"Арбитражный суд, обеспечение иска.\n"
                    f"Пошлина (ст. 333.21 НК РФ, пп. 17): {base:,.2f} ₽"
                ).replace(",", " ")
            else:
                base = 10_000.0
                detail = (
                    f"Суд общей юрисдикции, обеспечение иска.\n"
                    f"Пошлина (ст. 333.19 НК РФ, пп. 15): {base:,.2f} ₽"
                ).replace(",", " ")
            return base, detail

        # ── АПЕЛЛЯЦИЯ ─────────────────────────────────────────────────────────
        if ct == ClaimType.APPEAL:
            if is_arb:
                base = 30_000.0 if not is_ind else 10_000.0
            else:
                base = 15_000.0 if not is_ind else 3_000.0
            court_str = "арбитражный" if is_arb else "общей юрисдикции"
            detail = (
                f"Суд {court_str}, апелляционная жалоба.\n"
                f"Заявитель: {'физ. лицо' if is_ind else 'организация'}.\n"
                f"Пошлина (пп. 19): {base:,.2f} ₽"
            ).replace(",", " ")
            return base, detail

        # ── КАССАЦИЯ ──────────────────────────────────────────────────────────
        if ct == ClaimType.CASSATION:
            if is_arb:
                base = 50_000.0 if not is_ind else 20_000.0
            else:
                base = 20_000.0 if not is_ind else 5_000.0
            court_str = "арбитражный" if is_arb else "общей юрисдикции"
            detail = (
                f"Суд {court_str}, кассационная жалоба.\n"
                f"Заявитель: {'физ. лицо' if is_ind else 'организация'}.\n"
                f"Пошлина (пп. 20): {base:,.2f} ₽"
            ).replace(",", " ")
            return base, detail

        # ── ВЕРХОВНЫЙ СУД (кассация / надзор) ────────────────────────────────
        if ct == ClaimType.SUPREME_CASSATION:
            if is_arb:
                base = 80_000.0 if not is_ind else 30_000.0
            else:
                base = 25_000.0 if not is_ind else 7_000.0
            detail = (
                f"Верховный Суд РФ, кассационная / надзорная жалоба.\n"
                f"Заявитель: {'физ. лицо' if is_ind else 'организация'}.\n"
                f"Пошлина (пп. 21): {base:,.2f} ₽"
            ).replace(",", " ")
            return base, detail

        # ── БАНКРОТСТВО ───────────────────────────────────────────────────────
        if ct == ClaimType.BANKRUPTCY:
            base = 100_000.0 if not is_ind else 10_000.0
            detail = (
                f"Арбитражный суд, заявление о банкротстве.\n"
                f"Заявитель: {'физ. лицо' if is_ind else 'организация'}.\n"
                f"Пошлина (ст. 333.21 НК РФ, пп. 8): {base:,.2f} ₽"
            ).replace(",", " ")
            return base, detail

        # ── ОБОСОБЛЕННЫЙ СПОР В БАНКРОТСТВЕ ──────────────────────────────────
        if ct == ClaimType.BANKRUPTCY_DISPUTE:
            raw_base: float
            if self.claim_amount > 0:
                raw_base = _calc_arbitration_property(self.claim_amount)
                base = raw_base * 0.5
                detail = (
                    f"Арбитражный суд, обособленный спор в деле о банкротстве.\n"
                    f"Сумма требования: {self.claim_amount:,.2f} ₽\n"
                    f"Полная пошлина: {raw_base:,.2f} ₽\n"
                    f"50% → {base:,.2f} ₽\n"
                    f"(ст. 333.21 НК РФ, пп. 9)"
                ).replace(",", " ")
            else:
                # неимущественный обособленный спор
                raw_base = 50_000.0 if not is_ind else 15_000.0
                base = raw_base * 0.5
                detail = (
                    f"Арбитражный суд, обособленный спор (неимущественный).\n"
                    f"Заявитель: {'физ. лицо' if is_ind else 'организация'}.\n"
                    f"50% от {raw_base:,.2f} ₽ → {base:,.2f} ₽\n"
                    f"(ст. 333.21 НК РФ, пп. 9)"
                ).replace(",", " ")
            return base, detail

        # ── ИСПОЛНЕНИЕ ИНОСТРАННОГО / ТРЕТЕЙСКОГО РЕШЕНИЯ ────────────────────
        if ct == ClaimType.ENFORCEMENT_FOREIGN:
            if is_arb:
                raw_base = _calc_arbitration_property(self.claim_amount)
            else:
                raw_base = _calc_general_property(self.claim_amount)
            base = raw_base * 0.3
            detail = (
                f"Выдача исп. листа на реш. третейского / иностранного суда.\n"
                f"Подтверждённая сумма: {self.claim_amount:,.2f} ₽\n"
                f"Полная пошлина: {raw_base:,.2f} ₽\n"
                f"30% → {base:,.2f} ₽\n"
                f"(пп. 10/13 соответствующей статьи)"
            ).replace(",", " ")
            return base, detail

        # ── ОТМЕНА РЕШЕНИЯ ТРЕТЕЙСКОГО СУДА ──────────────────────────────────
        if ct == ClaimType.CANCEL_ARBITRATION:
            if is_arb:
                base = _calc_arbitration_property(self.claim_amount)
                detail = (
                    f"Арбитражный суд, отмена решения третейского суда.\n"
                    f"Оспариваемая сумма: {self.claim_amount:,.2f} ₽\n"
                    f"Пошлина (ст. 333.21 НК РФ, пп. 14): {base:,.2f} ₽"
                ).replace(",", " ")
            else:
                base = _calc_general_property(self.claim_amount)
                detail = (
                    f"Суд общей юрисдикции, отмена решения третейского суда.\n"
                    f"Оспариваемая сумма: {self.claim_amount:,.2f} ₽\n"
                    f"Пошлина (ст. 333.19 НК РФ, пп. 11): {base:,.2f} ₽"
                ).replace(",", " ")
            return base, detail

        # ── ПЕРЕСМОТР ПО НОВЫМ ОБСТОЯТЕЛЬСТВАМ ───────────────────────────────
        if ct == ClaimType.REVIEW_NEW_CIRCUMSTANCES:
            if is_arb:
                base = 30_000.0
                detail = (
                    f"Арбитражный суд, пересмотр по новым/вновь открывш. обст.\n"
                    f"Пошлина (ст. 333.21 НК РФ, пп. 16): {base:,.2f} ₽"
                ).replace(",", " ")
            else:
                base = 10_000.0
                detail = (
                    f"Суд общей юрисдикции, пересмотр по новым обстоятельствам.\n"
                    f"Пошлина (ст. 333.19 НК РФ, пп. 14): {base:,.2f} ₽"
                ).replace(",", " ")
            return base, detail

        # ── ДУБЛИКАТ ИСП. ЛИСТА / ПЕРЕСМОТР ЗАОЧНОГО ────────────────────────
        if ct == ClaimType.DUPLICATE_WRIT:
            if is_arb:
                base = 10_000.0
                detail = (
                    f"Арбитражный суд, дубликат исп. листа / отсрочка и т.п.\n"
                    f"Пошлина (ст. 333.21 НК РФ, пп. 15): {base:,.2f} ₽"
                ).replace(",", " ")
            else:
                base = 1_500.0
                detail = (
                    f"Суд общей юрисдикции, дубликат исп. листа / пересмотр заочного.\n"
                    f"Пошлина (ст. 333.19 НК РФ, пп. 12): {base:,.2f} ₽"
                ).replace(",", " ")
            return base, detail

        # ── ИСПОЛНИТЕЛЬНЫЕ ВОПРОСЫ (общая юрисдикция) ────────────────────────
        if ct == ClaimType.EXECUTION_ISSUES:
            base = 3_000.0
            detail = (
                f"Суд общей юрисдикции: отсрочка/рассрочка/разъяснение суд. постановления.\n"
                f"Пошлина (ст. 333.19 НК РФ, пп. 13): {base:,.2f} ₽"
            ).replace(",", " ")
            return base, detail

        # ── ПРАВОПРЕЕМСТВО ────────────────────────────────────────────────────
        if ct == ClaimType.SUCCESSION:
            if is_arb:
                base = 25_000.0 if not is_ind else 5_000.0
                detail = (
                    f"Арбитражный суд, правопреемство.\n"
                    f"Заявитель: {'физ. лицо' if is_ind else 'организация'}.\n"
                    f"Пошлина (ст. 333.21 НК РФ, пп. 12): {base:,.2f} ₽"
                ).replace(",", " ")
            else:
                base = 15_000.0 if not is_ind else 2_000.0
                detail = (
                    f"Суд общей юрисдикции, правопреемство.\n"
                    f"Заявитель: {'физ. лицо' if is_ind else 'организация'}.\n"
                    f"Пошлина (ст. 333.19 НК РФ, пп. 9): {base:,.2f} ₽"
                ).replace(",", " ")
            return base, detail

        # ── КОМПЕНСАЦИЯ ЗА НАРУШЕНИЕ РАЗУМНОГО СРОКА ─────────────────────────
        if ct == ClaimType.COMPENSATION_DELAY:
            base = 6_000.0 if not is_ind else 300.0
            detail = (
                f"Компенсация за нарушение разумного срока судопроизводства.\n"
                f"Заявитель: {'физ. лицо' if is_ind else 'организация'}.\n"
                f"Пошлина (пп. 17/18): {base:,.2f} ₽"
            ).replace(",", " ")
            return base, detail

        # ── КОМПЕНСАЦИЯ ЗА УСЛОВИЯ СОДЕРЖАНИЯ (только общ.) ─────────────────
        if ct == ClaimType.COMPENSATION_DETENTION:
            base = 300.0
            detail = (
                f"Компенсация за условия содержания под стражей.\n"
                f"Пошлина (ст. 333.19 НК РФ, пп. 18): {base:,.2f} ₽"
            ).replace(",", " ")
            return base, detail

        # ── ИС / ПАТЕНТЫ — НОРМАТИВНЫЙ АКТ ───────────────────────────────────
        if ct == ClaimType.IP_NORMATIVE:
            base = 60_000.0 if not is_ind else 10_000.0
            detail = (
                f"Арбитражный суд, оспаривание НПА в сфере ИС.\n"
                f"Заявитель: {'физ. лицо' if is_ind else 'организация'}.\n"
                f"Пошлина (ст. 333.21 НК РФ, пп. 5): {base:,.2f} ₽"
            ).replace(",", " ")
            return base, detail

        # ── ИС / ПАТЕНТЫ — РАЗЪЯСНИТЕЛЬНЫЙ АКТ ──────────────────────────────
        if ct == ClaimType.IP_CLARIFICATION:
            base = 60_000.0 if not is_ind else 10_000.0
            detail = (
                f"Арбитражный суд, оспаривание акта с разъяснениями (ИС).\n"
                f"Заявитель: {'физ. лицо' if is_ind else 'организация'}.\n"
                f"Пошлина (ст. 333.21 НК РФ, пп. 6): {base:,.2f} ₽"
            ).replace(",", " ")
            return base, detail

        raise ValueError(f"Неизвестный тип иска: {ct}")

    # ── Частичные льготы ─────────────────────────────────────────────────────

    def _apply_partial_exemption(
        self, base: float, details: str, warnings: list[str]
    ) -> tuple[float, str]:
        """
        Применить льготы, уменьшающие (но не обнуляющие) пошлину.

        Возвращает (итоговая_сумма, описание_льготы).
        """
        note = ""

        # ── Инвалиды I/II группы ──────────────────────────────────────────────
        # Освобождены, если пошлина ≤ 100 000 ₽; свыше — скидка 50%
        # НО для арбитражных судов льгота применяется при сумме иска ≤ 1 млн
        if self.exemption == ExemptionType.DISABILITY_1_2:
            if self.court_type == CourtType.GENERAL:
                if base <= 100_000:
                    warnings.append(
                        "Инвалиды I/II группы освобождены от пошлины, "
                        "если её размер не превышает 100 000 ₽ (ст. 333.36 НК РФ)."
                    )
                    return 0.0, "Инвалид I/II группы — полное освобождение (сумма ≤ 100 000 ₽)."
                else:
                    # свыше — не освобождаются
                    note = "Инвалид I/II группы: при пошлине > 100 000 ₽ льгота не применяется."
                    warnings.append(note)
            else:
                # Арбитраж: льгота при цене иска ≤ 1 000 000 ₽
                if self.claim_amount <= 1_000_000:
                    warnings.append(
                        "Арбитражный суд: инвалиды I/II группы освобождены при "
                        "цене иска ≤ 1 000 000 ₽ (ст. 333.37 НК РФ)."
                    )
                    return 0.0, "Инвалид I/II группы — полное освобождение (цена иска ≤ 1 000 000 ₽)."
                note = "Арбитраж: льгота инвалидов при цене иска > 1 000 000 ₽ не действует."
                warnings.append(note)

        # ── Защита прав потребителей ─────────────────────────────────────────
        if self.exemption == ExemptionType.CONSUMER_PROTECTION:
            effective_amount = (
                self.consumer_claim_amount
                if self.consumer_claim_amount is not None
                else self.claim_amount
            )
            if effective_amount <= 1_000_000:
                warnings.append(
                    "Потребитель освобождён от пошлины при цене иска ≤ 1 000 000 ₽."
                )
                return 0.0, "Защита прав потребителей — полное освобождение (цена иска ≤ 1 000 000 ₽)."
            else:
                # Пошлина считается только с суммы сверх 1 000 000 ₽
                excess = effective_amount - 1_000_000
                if self.court_type == CourtType.ARBITRATION:
                    reduced = _calc_arbitration_property(excess)
                else:
                    reduced = _calc_general_property(excess)
                note = (
                    f"Защита прав потребителей: пошлина считается только с суммы "
                    f"свыше 1 000 000 ₽ ({excess:,.2f} ₽)."
                ).replace(",", " ")
                warnings.append(note)
                return reduced, note

        return base, note
