# Routing Matrix

Use this matrix as strict default routing.

| Intent signal | Primary skill | Optional secondary |
|---|---|---|
| 人生、长期、未来几年、走势、格局 | `$oracle-ziwei-agent` | `$oracle-philosophy-rag-agent` |
| 今天、本周、近期事件、要不要做 | `$oracle-meihua-agent` | `$oracle-actionizer` |
| 牌阵、象征、内在状态（西方模式） | `$oracle-tarot-agent` | `$oracle-actionizer` |
| 每日卡片、今日宜忌 | `$oracle-daily-card-composer` | `$oracle-actionizer` |
| 情绪困扰、自我成长、修心 | `$oracle-philosophy-rag-agent` | `$oracle-actionizer` |

Hard rules:
- Always run `$oracle-safety-guardian` before and after generation.
- In east-only MVP, do not call tarot.
- For ambiguous intent, ask one clarifying question or provide dual-track answer (short + long) without contradiction.
