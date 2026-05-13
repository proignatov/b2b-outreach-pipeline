# B2B Cold Email Outreach Pipeline

Минимальная, воспроизводимая система outbound аутрича для B2B SaaS компаний (Россия + СНГ).

## Запуск

```bash
pip install requests beautifulsoup4
python3 scraper.py          # → outreach.csv (50 строк, raw data)

# опционально — LLM enrichment:
export ANTHROPIC_API_KEY=sk-ant-...
pip install anthropic
python3 enrich.py           # → outreach_enriched.csv (+ lpr_title, lpr_email, SDR инсайты)
```

## Файлы

| Файл | Описание |
|------|----------|
| `domains.txt` | 50 ICP-matched доменов (B2B SaaS, Россия+СНГ) |
| `scraper.py` | Scraping: title + meta + email → `outreach.csv` |
| `enrich.py` | LLM layer: LPR роль + SDR персонализация → `outreach_enriched.csv` |
| `outreach_enriched.csv` | Готовый датасет — 7 колонок, 50 строк |
| `email_sequence.md` | Цепочка 3 писем + архитектура пайплайна |
| `system_prompt.md` | Системный промпт для запуска через Claude Code |
| `vibe_stack.txt` | IDE и модели |

## Структура CSV

`company, website, lpr_title, lpr_email, icp_score, outreach_angle, personalization`

- **icp_score 3** (16 компаний) — CRM, martech, analytics: идеальный ICP
- **icp_score 2** (21 компания) — telephony, HR, payments: adjacent ICP  
- **icp_score 1** (13 компаний) — enterprise, security, edtech: слабый fit

## ICP (критерии отбора)

B2B SaaS или digital service, Россия/СНГ:
- есть сайт
- есть признаки отдела продаж или маркетинга
- продают сервис/софт другим бизнесам
- не микробизнес
