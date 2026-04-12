CONTRACT_TEMPLATES = {
    "nda": {
        "document_title": "Соглашение о неразглашении конфиденциальной информации (NDA)",
        "sections": [
            {
                "id": "parties",
                "label": "Стороны соглашения",
                "heading": "1. Стороны соглашения",
                "required": True,
                "field_ids": ["parties"],
                "instruction": "Опиши стороны соглашения, их статусы и, если есть, реквизиты."
            },
            {
                "id": "subject",
                "label": "Предмет соглашения",
                "heading": "2. Предмет соглашения",
                "required": True,
                "field_ids": ["subject"],
                "instruction": "Сформулируй цель передачи информации и предмет NDA."
            },
            {
                "id": "definition_confidential_info",
                "label": "Определение конфиденциальной информации",
                "heading": "3. Конфиденциальная информация",
                "required": True,
                "field_ids": ["definition_confidential_info"],
                "instruction": "Дай реалистичное юридическое определение конфиденциальной информации."
            },
            {
                "id": "obligations",
                "label": "Обязательства сторон",
                "heading": "4. Обязательства сторон",
                "required": True,
                "field_ids": ["obligations"],
                "instruction": "Опиши обязательства по неразглашению, хранению и использованию информации."
            },
            {
                "id": "liability",
                "label": "Ответственность сторон",
                "heading": "5. Ответственность сторон",
                "required": True,
                "field_ids": ["liability"],
                "instruction": "Опиши ответственность за нарушение NDA."
            },
            {
                "id": "term",
                "label": "Срок действия соглашения",
                "heading": "6. Срок действия соглашения",
                "required": False,
                "field_ids": ["term"],
                "instruction": "Укажи срок действия и, при необходимости, срок сохранения конфиденциальности."
            },
            {
                "id": "penalty",
                "label": "Штрафные санкции",
                "heading": "7. Штрафные санкции",
                "required": False,
                "field_ids": ["penalty"],
                "instruction": "Если есть данные, сформулируй штраф или неустойку."
            },
            {
                "id": "exceptions",
                "label": "Исключения из конфиденциальной информации",
                "heading": "8. Исключения из конфиденциальной информации",
                "required": False,
                "field_ids": ["exceptions"],
                "instruction": "Опиши допустимые исключения из режима конфиденциальности."
            },
            {
                "id": "dispute_resolution",
                "label": "Порядок разрешения споров",
                "heading": "9. Порядок разрешения споров",
                "required": False,
                "field_ids": ["dispute_resolution"],
                "instruction": "Укажи порядок досудебного урегулирования и суд."
            },
            {
                "id": "governing_law",
                "label": "Применимое право",
                "heading": "10. Применимое право",
                "required": False,
                "field_ids": ["governing_law"],
                "instruction": "Укажи применимое право, если оно задано."
            },
            {
                "id": "non_compete",
                "label": "Ограничение конкуренции",
                "heading": "11. Ограничение конкуренции",
                "required": False,
                "field_ids": ["non_compete"],
                "instruction": "Если это уместно, аккуратно опиши non-compete."
            },
        ],
    },

    "rent": {
        "document_title": "Договор аренды",
        "sections": [
            {
                "id": "parties",
                "label": "Стороны договора",
                "heading": "1. Стороны договора",
                "required": True,
                "field_ids": ["parties"],
                "instruction": "Опиши арендодателя и арендатора, их статусы и, если есть, реквизиты."
            },
            {
                "id": "subject",
                "label": "Предмет договора",
                "heading": "2. Предмет договора",
                "required": True,
                "field_ids": ["subject"],
                "instruction": "Опиши объект аренды и его характеристики."
            },
            {
                "id": "rent_payment",
                "label": "Арендная плата",
                "heading": "3. Арендная плата",
                "required": True,
                "field_ids": ["rent_payment"],
                "instruction": "Сформулируй размер арендной платы, периодичность и порядок оплаты."
            },
            {
                "id": "term",
                "label": "Срок аренды",
                "heading": "4. Срок аренды",
                "required": True,
                "field_ids": ["term"],
                "instruction": "Опиши срок аренды и порядок продления, если это уместно."
            },
            {
                "id": "rights_obligations",
                "label": "Права и обязанности сторон",
                "heading": "5. Права и обязанности сторон",
                "required": True,
                "field_ids": ["rights_obligations"],
                "instruction": "Сбалансированно опиши обязанности арендодателя и арендатора."
            },
            {
                "id": "deposit",
                "label": "Обеспечительный платеж",
                "heading": "6. Обеспечительный платеж",
                "required": False,
                "field_ids": ["deposit"],
                "instruction": "Если есть обеспечительный платеж, опиши его размер и возврат."
            },
            {
                "id": "utilities",
                "label": "Коммунальные услуги",
                "heading": "7. Коммунальные услуги",
                "required": False,
                "field_ids": ["utilities"],
                "instruction": "Опиши, кто оплачивает коммунальные и эксплуатационные расходы."
            },
            {
                "id": "maintenance",
                "label": "Содержание и ремонт",
                "heading": "8. Содержание и ремонт",
                "required": False,
                "field_ids": ["maintenance"],
                "instruction": "Опиши обязанности по содержанию, текущему и капитальному ремонту."
            },
            {
                "id": "termination",
                "label": "Условия расторжения",
                "heading": "9. Условия расторжения",
                "required": False,
                "field_ids": ["termination"],
                "instruction": "Укажи основания и порядок расторжения договора."
            },
            {
                "id": "liability",
                "label": "Ответственность сторон",
                "heading": "10. Ответственность сторон",
                "required": False,
                "field_ids": ["liability"],
                "instruction": "Опиши ответственность за просрочку, порчу имущества и иные нарушения."
            },
            {
                "id": "inspection",
                "label": "Порядок передачи имущества",
                "heading": "11. Порядок передачи имущества",
                "required": False,
                "field_ids": ["inspection"],
                "instruction": "Опиши передачу по акту и возврат имущества."
            },
            {
                "id": "sublease",
                "label": "Субаренда",
                "heading": "12. Субаренда",
                "required": False,
                "field_ids": ["sublease"],
                "instruction": "Укажи, разрешена ли субаренда и на каких условиях."
            },
            {
                "id": "pets",
                "label": "Условия содержания животных",
                "heading": "13. Условия содержания животных",
                "required": False,
                "field_ids": ["pets"],
                "instruction": "Если это важно, опиши условия содержания животных."
            },
            {
                "id": "dispute_resolution",
                "label": "Порядок разрешения споров",
                "heading": "14. Порядок разрешения споров",
                "required": False,
                "field_ids": ["dispute_resolution"],
                "instruction": "Опиши досудебный порядок и подсудность."
            },
        ],
    },

    "services": {
        "document_title": "Договор возмездного оказания услуг",
        "sections": [
            {
                "id": "parties",
                "label": "Стороны договора",
                "heading": "1. Стороны договора",
                "required": True,
                "field_ids": ["parties"],
                "instruction": "Опиши заказчика и исполнителя, их статусы и, если есть, реквизиты."
            },
            {
                "id": "subject",
                "label": "Предмет договора",
                "heading": "2. Предмет договора",
                "required": True,
                "field_ids": ["subject"],
                "instruction": "Сформулируй, какие услуги оказываются и в каком объеме."
            },
            {
                "id": "services_description",
                "label": "Описание услуг",
                "heading": "3. Описание услуг",
                "required": True,
                "field_ids": ["services_description"],
                "instruction": "Раскрой состав, объем и ожидаемый результат услуг."
            },
            {
                "id": "price_payment",
                "label": "Стоимость и порядок оплаты",
                "heading": "4. Стоимость и порядок оплаты",
                "required": True,
                "field_ids": ["price_payment"],
                "instruction": "Опиши цену, порядок расчетов, аванс, сроки оплаты."
            },
            {
                "id": "term",
                "label": "Срок оказания услуг",
                "heading": "5. Срок оказания услуг",
                "required": True,
                "field_ids": ["term"],
                "instruction": "Укажи срок оказания услуг и возможное продление."
            },
            {
                "id": "acceptance",
                "label": "Порядок приемки услуг",
                "heading": "6. Порядок приемки услуг",
                "required": False,
                "field_ids": ["acceptance"],
                "instruction": "Опиши порядок сдачи-приемки результатов услуг."
            },
            {
                "id": "liability",
                "label": "Ответственность сторон",
                "heading": "7. Ответственность сторон",
                "required": False,
                "field_ids": ["liability"],
                "instruction": "Сбалансированно опиши ответственность за нарушение договора."
            },
            {
                "id": "penalty",
                "label": "Штрафные санкции",
                "heading": "8. Штрафные санкции",
                "required": False,
                "field_ids": ["penalty"],
                "instruction": "Если уместно, опиши неустойку или штраф."
            },
            {
                "id": "confidentiality",
                "label": "Конфиденциальность",
                "heading": "9. Конфиденциальность",
                "required": False,
                "field_ids": ["confidentiality"],
                "instruction": "Добавь условия о неразглашении, если они есть."
            },
            {
                "id": "ip_rights",
                "label": "Права на результаты работ",
                "heading": "10. Права на результаты работ",
                "required": False,
                "field_ids": ["ip_rights"],
                "instruction": "Если услуги связаны с результатом интеллектуальной деятельности, опиши права на результат."
            },
            {
                "id": "termination",
                "label": "Условия расторжения",
                "heading": "11. Условия расторжения",
                "required": False,
                "field_ids": ["termination"],
                "instruction": "Укажи основания и порядок расторжения договора."
            },
            {
                "id": "force_majeure",
                "label": "Форс-мажор",
                "heading": "12. Форс-мажор",
                "required": False,
                "field_ids": ["force_majeure"],
                "instruction": "Опиши обстоятельства непреодолимой силы."
            },
            {
                "id": "subcontracting",
                "label": "Привлечение третьих лиц",
                "heading": "13. Привлечение третьих лиц",
                "required": False,
                "field_ids": ["subcontracting"],
                "instruction": "Укажи, допускается ли привлечение третьих лиц."
            },
            {
                "id": "dispute_resolution",
                "label": "Порядок разрешения споров",
                "heading": "14. Порядок разрешения споров",
                "required": False,
                "field_ids": ["dispute_resolution"],
                "instruction": "Опиши досудебный порядок и подсудность."
            },
        ],
    },
}